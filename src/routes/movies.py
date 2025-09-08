from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_filter import FilterDepends
from sqlalchemy import select, Result, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from starlette import status
from starlette.responses import JSONResponse

from src.database.models import PaymentModel, OrderModel, OrderItemModel
from src.database.models.accounts import UserModel, UserGroupEnum
from src.database.models.movies import (
    Movie,
    Certification,
    Genre,
    Director,
    Star,
    Comment,
    Rate,
    Notification,
)
from src.database.models.payments import PaymentStatus
from src.database import get_db
from src.querying.movie_filtering import MovieFilter
from src.querying.movie_sorting import ItemQueryParams
from src.schemas.movies import (
    MovieCreateSchema,
    MoviesPaginationResponse,
    MovieCreateResponse,
    MovieDetailResponse,
    CommentSchema,
    MoviesForGenreResponse,
    ScoreRequestSchema,
    MovieUpdate,
)
from src.security.token_manipulation import get_current_user

router = APIRouter()


@router.post(
    "/create/",
    response_model=MovieCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Creation movie",
    description="Create a new movie entry in the database "
    "with details such as name, year, "
    "genres, directors, stars, and certification. "
    "Returns the full movie record.",
)
async def film_create(
    schema: MovieCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Creation movie

    schema (MovieCreateSchema): The creation details.
    db (AsyncSession): The asynchronous database session.
    current_user (User): The authenticated user performing the action.
    return: MovieCreateResponse: The created movie with all related details.
    """

    stmt_user = select(UserModel).where(UserModel.id == current_user.id)
    result_user = await db.execute(stmt_user)
    user = result_user.scalars().first()

    if user.group.name != UserGroupEnum.MODERATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: insufficient permissions.",
        )
    try:

        cert_stmt = select(Certification).where(
            Certification.name == schema.certification
        )
        result: Result = await db.execute(cert_stmt)
        certification = result.scalars().first()
        if not certification:
            certification = Certification(name=schema.certification)
            db.add(certification)
            await db.flush()

        genres_list = []
        for genre_name in schema.genres:
            genres_stmt = select(Genre).where(Genre.name == genre_name)
            result: Result = await db.execute(genres_stmt)
            genre = result.scalars().first()
            if not genre:
                genre = Genre(name=genre_name)
                db.add(genre)
                await db.flush()
            genres_list.append(genre)

        directors_list = []
        for director_name in schema.directors:
            dir_stmt = select(Director).where(Director.name == director_name)
            result: Result = await db.execute(dir_stmt)
            director = result.scalars().first()
            if not director:
                director = Director(name=director_name)
                db.add(director)
                await db.flush()
            directors_list.append(director)

        stars_list = []
        for star_name in schema.stars:
            star_stmt = select(Star).where(Star.name == star_name)
            result: Result = await db.execute(star_stmt)
            star = result.scalars().first()
            if not star:
                star = Star(name=star_name)
                db.add(star)
                await db.flush()
            stars_list.append(star)

        new_movie = Movie(
            name=schema.name,
            year=schema.year,
            time=schema.time,
            imdb=schema.imdb,
            votes=schema.votes,
            meta_score=schema.meta_score,
            gross=schema.gross,
            description=schema.description,
            price=schema.price,
            certification=certification,
            genres=genres_list,
            directors=directors_list,
            stars=stars_list,
        )

        db.add(new_movie)
        await db.commit()
        await db.refresh(new_movie, ["genres", "directors", "stars"])
        return MovieCreateResponse(
            id=new_movie.id,
            name=new_movie.name,
            year=new_movie.year,
            time=new_movie.time,
            imdb=new_movie.imdb,
            votes=new_movie.votes,
            meta_score=new_movie.meta_score,
            gross=new_movie.gross,
            description=new_movie.description,
            price=new_movie.price,
            certification=new_movie.certification.name,
            genres=[g.name for g in new_movie.genres],
            directors=[d.name for d in new_movie.directors],
            stars=[s.name for s in new_movie.stars],
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"error: {str(e)}")


@router.patch(
    "/update/{movie_id}/",
    status_code=status.HTTP_200_OK,
    summary="Update movie by ID",
    description=(
        "<h3>Update details of a specific movie by its unique ID.</h3>"
        "<p>This endpoint updates the details of an existing movie. "
        "If the movie with "
        "the given ID does not exist, a 404 error is returned.</p>"
    ),
)
async def movie_update(
    movie_id: int,
    schema: MovieUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update an existing movie by ID.

    :param movie_id: The unique ID of the movie to update.
    :type movie_id: int
    :param schema: The fields to update, provided as a Pydantic model.
    :param current_user: The currently
    authenticated user (must be a moderator).
    :param db: The asynchronous database session.
    :return: A dictionary with the updated movie object.
    :rtype: dict
    :raises HTTPException 403: If the user does not have moderator permissions.
    :raises HTTPException 404: If the movie is not found.
    """
    stmt_movie = select(Movie).where(Movie.id == movie_id)
    result: Result = await db.execute(stmt_movie)
    movie = result.scalars().first()

    stmt_user = select(UserModel).where(UserModel.id == current_user.id)
    result_user: Result = await db.execute(stmt_user)
    user = result_user.scalars().first()

    if user.group.name != UserGroupEnum.MODERATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: insufficient permissions.",
        )

    trash_values = {None}
    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )
    for field, value in schema.model_dump(exclude_unset=True).items():
        if value in trash_values:
            continue
        setattr(movie, field, value)
    await db.commit()
    await db.refresh(movie)
    return {"new movie": movie}


@router.delete(
    "/delete/{movie_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete movie by ID",
    description="Deletes a movie from the database by its unique ID. "
    "If the movie does not exist, returns 404 Not Found.",
)
async def movie_delete(
    movie_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete an existing movie by ID.

    :param movie_id: The unique ID of the movie to delete.
    :type: int
    :param current_user: The currently
    authenticated user (must be a moderator).
    :type: UserModel
    :param db: The asynchronous database session.
    :type: AsyncSession
    :return: Dictionary with a message about successful deletion
    """
    stmt_movie = select(Movie).where(Movie.id == movie_id)
    result: Result = await db.execute(stmt_movie)
    movie = result.scalars().first()

    stmt_user = select(UserModel).where(UserModel.id == current_user.id)
    result: Result = await db.execute(stmt_user)
    user = result.scalars().first()

    if user.group.name != UserGroupEnum.MODERATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden for {user.group.name}: "
            f"insufficient permissions.",
        )

    stmt = (
        select(PaymentModel)
        .join(PaymentModel.order)
        .join(OrderModel.order_items)
        .join(OrderItemModel.movie)
        .options(
            selectinload(PaymentModel.order)
            .selectinload(OrderModel.order_items)
            .selectinload(OrderItemModel.movie)
        )
        .where(
            OrderItemModel.movie_id == movie_id,
            PaymentModel.status == PaymentStatus.SUCCESSFUL,
        )
    )
    result: Result = await db.execute(stmt)
    payment = result.scalars().first()
    if payment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="current film is bought"
        )

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="movie not found"
        )

    await db.delete(movie)
    await db.commit()

    return {"detail": "Movie deleted successfully"}


@router.get(
    "/lists/",
    response_model=MoviesPaginationResponse,
    status_code=status.HTTP_200_OK,
    summary="List of movies",
    description=(
        "Returns a paginated list of movies from the database. "
        "Supports filtering by fields (e.g., genre, year, rating) "
        "and sorting by different attributes. "
        "Pagination is controlled with `page` and `per_page` parameters."
    ),
)
async def movie_list(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1),
    movie_filter: MovieFilter = FilterDepends(MovieFilter),
    sort: ItemQueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a list of movies with pagination, filtering, and sorting support.

    :param page: Page number (starting from 1).
    :type page: int
    :param per_page: Number of movies per page.
    :type per_page: int
    :param movie_filter: Filters for selecting movies
    (e.g., genre, director, etc.).
    :type movie_filter: MovieFilter
    :param sort: Sorting parameters for the movie list.
    :type sort: ItemQueryParams
    :param db: Async database session.
    :type db: AsyncSession
    :return: Object containing a paginated list of movies.
    :rtype: MoviesPaginationResponse
    """
    order_column = getattr(Movie, sort.order_by)
    if sort.descending:
        order_column = order_column.desc()

    stmt = movie_filter.filter(select(Movie).order_by(order_column))
    result: Result = await db.execute(stmt)
    movies = result.scalars().all()

    start = (page - 1) * per_page
    end = start + per_page
    paginated_items = movies[start:end]
    if not paginated_items:
        raise HTTPException(status_code=404, detail="No movies found.")
    stmt_total = select(func.count(Movie.id))
    result: Result = await db.execute(stmt_total)
    total_items = result.scalars().first()
    total_pages = (total_items + per_page - 1) // per_page

    return MoviesPaginationResponse(
        movies=[item for item in paginated_items],
        prev_page=f"/movies/?page={page - 1}&per_page={per_page}"
        if page > 1 else None,
        next_page=(
            f"/movies/?page={page + 1}&per_page={per_page}"
            if page < total_pages
            else None
        ),
        total_pages=total_pages,
        total_items=total_items,
    )


@router.post(
    "/search/",
    response_model=List[MovieDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Search movies",
    description=(
        "Search movies from the database"
        "Returns list of found movies"
        "Search by fields (e.g. name, description, stars, directors)"
    ),
)
async def movie_search(
    search: Optional[str] = None, db: AsyncSession = Depends(get_db)
):
    """
    Search existing movies by specific fields.

    :param search: Search query string
    (e.g., title, genres, directors, stars).
    :type search: str
    :param db: Async database session.
    :type db: AsyncSession
    :return: List of matching movies.
    :rtype: list[Movie]
    """
    stmt = (
        select(Movie)
        .options(joinedload(Movie.certification))
        .options(joinedload(Movie.genres))
        .options(joinedload(Movie.directors))
        .options(joinedload(Movie.stars))
        .options(selectinload(Movie.comments).selectinload(Comment.user))
    )
    result: Result = await db.execute(stmt)
    movies = result.unique().scalars().all()
    seen_movie_ids = set()
    if search:
        list_search = []
        for item in movies:
            if (
                    search.lower() in item.name.lower()
                    and item.id not in seen_movie_ids
            ):
                list_search.append(item)
                seen_movie_ids.add(item.id)

            if (
                search.lower() in item.description.lower()
                and item.id not in seen_movie_ids
            ):
                list_search.append(item)
                seen_movie_ids.add(item.id)

            for actor in item.stars:
                if (
                    search.lower() in actor.name.lower()
                    and item.id not in seen_movie_ids
                ):
                    list_search.append(item)
                    seen_movie_ids.add(item.id)

            for director in item.directors:
                if (
                    search.lower() in director.name.lower()
                    and item.id not in seen_movie_ids
                ):
                    list_search.append(item)
                    seen_movie_ids.add(item.id)
        return list_search

    return movies


@router.get(
    "/detail/",
    response_model=MovieDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Movie detail",
    description="Returns detailed movie by movie id",
)
async def movie_detail(movie_id: int, db: AsyncSession = Depends(get_db)):
    """
    Returns detailed information about a specific movie by its ID.

    :param movie_id: The unique ID of the movie.
    :type: int
    :param db: Async database session
    :type: AsyncSession
    :return: Dictionary with a found movie
    :rtype: dict
    """
    stmt = (
        select(Movie)
        .where(Movie.id == movie_id)
        .options(joinedload(Movie.certification))
        .options(joinedload(Movie.genres))
        .options(joinedload(Movie.directors))
        .options(joinedload(Movie.stars))
        .options(selectinload(Movie.comments).selectinload(Comment.user))
    )
    result: Result = await db.execute(stmt)
    movie = result.scalars().first()

    return movie


@router.post(
    "/like/{movie_id}/",
    status_code=status.HTTP_201_CREATED,
    summary="Like movie",
    description="Add or remove a like for a movie by its ID.",
)
async def add_and_remove_like(
    movie_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns adding/removing like on specific movie by its ID.

    :param movie_id: The unique ID of the movie.
    :type: int
    :param current_user: The currently authenticated user.
    :type: UserModel
    :param db: Async database session
    :type: AsyncSession
    :return: Dictionary obout likes count
    """
    stmt = (
        select(Movie)
        .options(selectinload(Movie.like_users))
        .where(Movie.id == movie_id)
    )
    result: Result = await db.execute(stmt)
    movie = result.scalars().first()

    user_stmt = select(UserModel).where(UserModel.id == current_user.id)
    result: Result = await db.execute(user_stmt)
    user = result.scalars().first()

    if user in movie.like_users:
        movie.like_count -= 1
        movie.like_users.remove(user)
    else:
        movie.like_count += 1
        movie.like_users.append(user)

    await db.commit()
    return {"like_count": movie.like_count}


@router.post(
    "/{movie_id}/comments/",
    status_code=status.HTTP_201_CREATED,
    summary="Add comment to movie",
    description="Create a new comment for a movie specified by its ID.",
)
async def write_comments(
    movie_id: int,
    schema: CommentSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns new comment for the movie

    :param movie_id: The unique ID of the movie.
    :type: int
    :param schema: The request body containing the comment data
    :type: CommentSchema
    :param current_user: The currently authenticated user.
    :param db: Async database session
    :type: AsyncSession
    :return: The newly created comment object linked to the movie.
    :rtype: Comment
    """
    stmt_user = select(UserModel).where(UserModel.id == current_user.id)
    result_user: Result = await db.execute(stmt_user)
    user = result_user.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    stmt_movie = select(Movie).where(Movie.id == movie_id)
    result_movie: Result = await db.execute(stmt_movie)
    movie = result_movie.scalars().first()

    db_comment = Comment(
        comment=schema.comments,
        user_id=user.id,
        movie_id=movie.id
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment


@router.post(
    "/favourite/{movie_id}/",
    summary="Create/remove favorite movie",
    description="Add a movie to the user's favorites "
    "list or remove it if it's already marked as favorite.",
)
async def add_and_remove_favourite(
    movie_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Toggle a movie in the user's favorites list.

    :param movie_id: The unique ID of the
    movie to add or remove from favorites.
    :type movie_id: int
    :param current_user: The currently authenticated user.
    :type current_user: UserModel
    :param db: Database session dependency.
    :type db: AsyncSession
    :return: A JSON response containing a success message.
    :rtype: JSONResponse
    """
    stmt_user = (
        select(UserModel)
        .options(selectinload(UserModel.favourite_movies))
        .where(UserModel.id == current_user.id)
    )
    result: Result = await db.execute(stmt_user)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is unauthorized"
        )

    stmt_movie = select(Movie).where(Movie.id == movie_id)
    result: Result = await db.execute(stmt_movie)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found"
        )

    if movie not in user.favourite_movies:
        user.favourite_movies.append(movie)
        message = "added to favourite"
        response_status = status.HTTP_201_CREATED
    else:
        user.favourite_movies.remove(movie)
        message = "remove from favourite"
        response_status = status.HTTP_200_OK
    db.add(user)
    await db.commit()

    return JSONResponse(
        content={"message": message},
        status_code=response_status
    )


@router.get(
    "/favourite/list/",
    status_code=status.HTTP_200_OK,
    summary="List of favourite movies",
    description="Return list of favourite movies from the database.",
)
async def favourite_list(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the list of favorite movies for the authenticated user.

    :param current_user: The currently authenticated user.
    :type current_user: UserModel
    :param db: Database session dependency.
    :type db: AsyncSession
    :return: A list of movies marked as favorite by the user.
    :rtype: List[Movie]
    """
    stmt_user = (
        select(UserModel)
        .options(selectinload(UserModel.favourite_movies))
        .where(UserModel.id == current_user.id)
    )
    result: Result = await db.execute(stmt_user)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is unauthorized"
        )

    return user.favourite_movies


@router.get(
    "/favourite/search/",
    status_code=status.HTTP_200_OK,
    summary="search favourite movies",
    description=(
        "Search FAVOURITE movies from the database"
        "Returns list of found movies"
        "Search by fields (e.g. name, description, stars, directors)"
    ),
)
async def favourite_search(
    search: Optional[str] = Query(None),
    current_user: UserModel = Depends(get_current_user),
    movie_filter: MovieFilter = FilterDepends(MovieFilter),
    sort: ItemQueryParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a list of favourite movies with filtering, and sorting support.

    :param search: Search query string (e.g., title, genres, directors, stars).
    :type search: str
    :param current_user: The currently authenticated user.
    :type current_user: UserModel
    :param movie_filter: Filters for
    selecting movies (e.g., genre, director, etc.).
    :type movie_filter: MovieFilter
    :param sort: Sorting parameters for the movie list.
    :type sort: ItemQueryParams
    :param db: Async database session.
    :type db: AsyncSession
    :return: Dictionary containing list of movies.
    :rtype: dict
    """
    stmt = (
        select(UserModel)
        .options(
            selectinload(UserModel.favourite_movies)
            .selectinload(Movie.directors),
            selectinload(UserModel.favourite_movies).selectinload(Movie.stars),
        )
        .where(UserModel.id == current_user.id)
    )
    result: Result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is unauthorized"
        )
    search_list = user.favourite_movies
    if search:
        search_list = []
        for item in user.favourite_movies:
            if search.lower() in item.name.lower():
                search_list.append(item)
            if search.lower() in item.description.lower():
                search_list.append(item)

            for actor in item.stars:
                if search.lower() in actor.name.lower():
                    search_list.append(item)
            for director in item.directors:
                if search.lower() in director.name.lower():
                    search_list.append(item)
    unique_movies = {movie.id: movie for movie in search_list}.values()

    if movie_filter:
        filtered_list = []
        for movie in unique_movies:
            if movie_filter.year and movie.year != movie_filter.year:
                continue
            if movie_filter.imdb and movie.imdb < movie_filter.imdb:
                continue
            filtered_list.append(movie)

    else:
        filtered_list = unique_movies

    if sort:
        filtered_list = sorted(
            filtered_list,
            key=lambda m: getattr(m, sort.order_by),
            reverse=sort.descending,
        )

    return filtered_list


@router.get(
    "/genre/{genre_id}/",
    response_model=MoviesForGenreResponse,
    status_code=status.HTTP_200_OK,
    summary="Movies of genre",
    description="Search movies by genre ID",
)
async def movies_of_genre(
    genre_id: Optional[int] = None, db: AsyncSession = Depends(get_db)
):
    """
    Get all movies for a specific genre.

    :param genre_id: The unique ID of the genre to filter movies.
    :type genre_id: int
    :param db: Async database session.
    :type db: AsyncSession
    :return: A response containing the list of movies
    for the genre, all genres, and the total movie count.
    :rtype: MoviesForGenreResponse
    """
    stmt_movies = (
        select(Movie)
        .join(Movie.genres)
        .options(joinedload(Movie.genres))
        .where(Genre.id == genre_id)
    )
    result: Result = await db.execute(stmt_movies)
    movies = result.unique().scalars().all()
    if not movies:
        raise HTTPException(status_code=404, detail="Movies not found")

    stmt_movies = (
        select(func.count(Movie.id))
        .select_from(Movie)
        .join(Movie.genres)
        .where(Genre.id == genre_id)
    )
    result: Result = await db.execute(stmt_movies)
    count_movies = result.scalars().first()

    stmt_genres = select(Genre)
    result_genres: Result = await db.execute(stmt_genres)
    genres = result_genres.scalars().all()
    return MoviesForGenreResponse(
        count_movies=count_movies, genres=genres, movies=movies
    )


@router.post(
    "/score/{movie_id}/",
    status_code=status.HTTP_201_CREATED,
    summary="Score of the movie",
    description="Add score of the rating by movie",
)
async def rate(
    movie_id: int,
    schema: ScoreRequestSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add score of the movie to database for the authenticated user.

    :param movie_id: The unique ID of the movie.
    :type movie_id: int
    :param schema: The request body containing the score data.
    :type schema: ScoreRequestSchema
    :param current_user: The currently authenticated user.
    :type current_user: UserModel
    :param db: Database session dependency.
    :type: AsyncSession
    :return: Dictionary of new score
    :rtype: dict
    """
    stmt_rate = select(Rate).where(
        Rate.movie_id == movie_id, Rate.user_id == current_user.id
    )
    result: Result = await db.execute(stmt_rate)
    rate = result.scalars().first()

    stmt_movie = select(Movie).where(Movie.id == movie_id)
    result: Result = await db.execute(stmt_movie)
    movie = result.scalars().first()

    if not rate:
        new_rate = Rate(
            rate=schema.score,
            user_id=current_user.id,
            movie_id=movie_id
        )
        movie.votes += 1
        db.add(new_rate)
        await db.commit()
        await db.refresh(new_rate)
        return {"message": f"new rate - {new_rate.rate}"}

    rate.rate = schema.score
    await db.commit()
    await db.refresh(rate)
    return {"message": f"updated rate - {rate.rate}"}


@router.post(
    "/notification/{comment_id}/",
    status_code=status.HTTP_200_OK,
    summary="Comment for notification",
    description="Notifies the user about a received comment by the comment ID",
)
async def notification_comment(
    comment_id: int,
    schema: CommentSchema,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a notification to a user about a received comment.

    :param comment_id: The unique ID of the comment
    that triggered the notification.
    :type comment_id: int
    :param schema: The comment data payload.
    :type schema: CommentSchema
    :param current_user: The authenticated user sending the notification.
    :type current_user: UserModel
    :param db: Database session dependency.
    :type db: AsyncSession
    :return: A dictionary containing the newly created notification.
    :rtype: dict
    """
    stmt_user = select(UserModel).where(UserModel.id == current_user.id)
    result: Result = await db.execute(stmt_user)
    user = result.scalars().first()

    comment = await db.get(Comment, comment_id)
    db_comment = Comment(comment=schema.comments, user_id=user.id)
    db.add(db_comment)
    await db.flush()
    new_notif = Notification(
        user_id=comment.user_id,
        comment_id=comment.id,
        message=f"{user.email} replied you",
    )

    db.add(new_notif)
    await db.commit()
    return {"new notification": new_notif}
