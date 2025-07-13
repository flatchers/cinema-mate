from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_filter import FilterDepends
from sqlalchemy import select, Result, func, delete
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette import status

from src.database.models.accounts import UserModel, UserGroupEnum, UserGroup
from src.database.models.movies import Movie, Certification, Genre, Director, Star, Comment, Rate, Notification
from src.database.session_sqlite import get_db
from src.querying.movie_filtering import MovieFilter
from src.querying.movie_sorting import ItemQueryParams
from src.schemas.movies import (
    MovieCreateSchema,
    MoviesPaginationResponse,
    MovieCreateResponse,
    MovieDetailResponse, CommentSchema, MoviesForGenreResponse, ScoreRequestSchema, MovieUpdate,
)
from src.security.token_manipulation import get_current_user

router = APIRouter()


""" CRUD OPERATIONS FOR MODERATORS """


@router.post("/create/", response_model=MovieCreateResponse, status_code=status.HTTP_201_CREATED)
async def film_create(
        schema: MovieCreateSchema,
        db: AsyncSession = Depends(get_db),
        current_user: UserModel = Depends(get_current_user)

):

    stmt_user = select(UserModel).where(UserModel.id == current_user.id)
    result_user = await db.execute(stmt_user)
    user = result_user.scalars().first()

    if user.group.name != UserGroupEnum.MODERATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden: insufficient permissions.")
    try:

        cert_stmt = select(Certification).where(Certification.name == schema.certification)
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
            stars=stars_list
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


@router.patch("/update/{movie_id}/")
async def movie_update(
        movie_id: int,
        schema: MovieUpdate,
        current_user = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    stmt_movie = select(Movie).where(
        Movie.id == movie_id
    )
    result: Result = await db.execute(stmt_movie)
    movie = result.scalars().first()

    stmt_user = select(UserModel).where(UserModel.id == current_user.id)
    result_user: Result = await db.execute(stmt_user)
    user = result_user.scalars().first()

    if user.group.name != UserGroupEnum.MODERATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden: insufficient permissions.")

    trash_values = {None}
    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Movie not found")
    for field, value in schema.model_dump(exclude_unset=True).items():
        if value in trash_values:
            continue
        setattr(movie, field, value)
    await db.commit()
    await db.refresh(movie)
    return {"new movie": movie}


@router.delete("/delete/{movie_id}")
async def movie_delete(
        movie_id: int,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    stmt_movie = select(Movie).where(Movie.id == movie_id)
    result: Result = await db.execute(stmt_movie)
    movie = result.scalars().first()

    stmt_user = select(UserModel).where(UserModel.id == current_user.id)
    result: Result = await db.execute(stmt_user)
    user = result.scalars().first()

    if user.group.name != UserGroupEnum.MODERATOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access forbidden for {user.group.name}: insufficient permissions."
        )

    if not movie:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="movie not found")

    await db.delete(movie)
    await db.commit()

    return "Movie deleted successfully"


@router.get("/lists/", response_model=MoviesPaginationResponse, status_code=status.HTTP_200_OK)
async def movie_list(
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1),
        movie_filter: MovieFilter = FilterDepends(MovieFilter),
        sort: ItemQueryParams = Depends(),
        db: AsyncSession = Depends(get_db)
):
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
        prev_page=f"/movies/?page={page - 1}&per_page={per_page}" if page > 1 else None,
        next_page=f"/movies/?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        total_pages=total_pages,
        total_items=total_items
    )


@router.post("/search/", response_model=List[MovieDetailResponse], status_code=status.HTTP_200_OK)
async def movie_search(search: Optional[str] = None, db: AsyncSession = Depends(get_db)):

    stmt = (select(Movie)
            .options(selectinload(Movie.certification))
            .options(selectinload(Movie.genres))
            .options(selectinload(Movie.directors))
            .options(selectinload(Movie.stars))
            .options(selectinload(Movie.comments).selectinload(Comment.user))
            )
    result: Result = await db.execute(stmt)
    movies = result.scalars().all()

    if search:
        list_search = []
        for item in movies:
            if search.lower() in item.name.lower():
                list_search.append(item)

            if search.lower() in item.description.lower():
                list_search.append(item)

            for actor in item.stars:
                if search.lower() in actor.name.lower():
                    list_search.append(item)

            for director in item.directors:
                if search.lower() in director.name.lower():
                    list_search.append(item)
        return list_search

    return movies


@router.get("/detail/", response_model=MovieDetailResponse, status_code=status.HTTP_200_OK)
async def movie_detail(movie_id: int, db: AsyncSession = Depends(get_db)):

    stmt = (select(Movie).where(Movie.id == movie_id)
            .options(selectinload(Movie.certification))
            .options(selectinload(Movie.genres))
            .options(selectinload(Movie.directors))
            .options(selectinload(Movie.stars))
            .options(selectinload(Movie.comments).selectinload(Comment.user))
            )
    result: Result = await db.execute(stmt)
    movie = result.scalars().first()

    return movie


@router.post("/{movie_id}/like/", status_code=status.HTTP_201_CREATED)
async def add_and_remove_like(
        movie_id: int,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    stmt = select(Movie).options(selectinload(Movie.like_users)).where(Movie.id == movie_id)
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


@router.post("/{movie_id}/comments/", status_code=status.HTTP_201_CREATED)
async def write_comments(
        movie_id: int,
        schema: CommentSchema,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):

    stmt_user = select(UserModel).where(UserModel.id == current_user.id)
    result_user: Result = await db.execute(stmt_user)
    user = result_user.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    stmt_movie = select(Movie).where(Movie.id == movie_id)
    result_movie: Result = await db.execute(stmt_movie)
    movie = result_movie.scalars().first()

    db_comment = Comment(comment=schema.comments, user_id=user.id, movie_id=movie.id)
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return db_comment


@router.post("/{movie_id}/favourite/", status_code=status.HTTP_201_CREATED)
async def add_and_remove_favourite(
        movie_id: int,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    stmt_user = (select(UserModel)
                 .options(selectinload(UserModel.favourite_movies))
                 .where(UserModel.id == current_user.id)
                 )
    result: Result = await db.execute(stmt_user)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is unauthorized")

    stmt_movie = select(Movie).where(Movie.id == movie_id)
    result: Result = await db.execute(stmt_movie)
    movie = result.scalars().first()

    if not movie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Movie not found")

    if movie not in user.favourite_movies:
        user.favourite_movies.append(movie)
        message = "added to favourite"
    else:
        user.favourite_movies.remove(movie)
        message = "remove from favourite"
    await db.commit()
    return {"message": message}


@router.get("/favourite/list/")
async def favourite_list(current_user: UserModel = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt_user = (select(UserModel)
                 .options(selectinload(UserModel.favourite_movies))
                 .where(UserModel.id == current_user.id)
                 )
    result: Result = await db.execute(stmt_user)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is unauthorized")

    return user.favourite_movies


@router.post("/favourite/search/", status_code=status.HTTP_200_OK)
async def favourite_search(
        search: Optional[str] = None,
        current_user: UserModel = Depends(get_current_user),
        movie_filter: MovieFilter = FilterDepends(MovieFilter),
        sort: ItemQueryParams = Depends(),
        db: AsyncSession = Depends(get_db)
):

    stmt = select(UserModel).options(
        selectinload(UserModel.favourite_movies)
        .selectinload(Movie.directors),
        selectinload(UserModel.favourite_movies)
        .selectinload(Movie.stars)
    ).where(UserModel.id == current_user.id)
    result: Result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is unauthorized")
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
        filtered_list = sorted(filtered_list, key=lambda m: getattr(m, sort.order_by), reverse=sort.descending)

    return filtered_list


@router.get("/genre/{genre_id}/", response_model=MoviesForGenreResponse, status_code=status.HTTP_200_OK)
async def movies_of_genre(genre_id: Optional[int] = None, db: AsyncSession = Depends(get_db)):
    stmt_movies = select(Movie).join(Movie.genres).options(selectinload(Movie.genres)).where(Genre.id == genre_id)
    result: Result = await db.execute(stmt_movies)
    movies = result.scalars().all()

    stmt_movies = (
        select(func.count(Movie.id))
        .select_from(Movie)
        .join(Movie.genres)
        .where(Genre.id == genre_id))
    result: Result = await db.execute(stmt_movies)
    count_movies = result.scalars().first()

    stmt_genres = (select(Genre))
    result_genres: Result = await db.execute(stmt_genres)
    genres = result_genres.scalars().all()
    return MoviesForGenreResponse(count_movies=count_movies, genres=genres, movies=movies)


@router.post("/score/{movie_id}/", status_code=status.HTTP_201_CREATED)
async def rate(
        movie_id: int,
        schema: ScoreRequestSchema,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    stmt_rate = select(Rate).where(Rate.movie_id == movie_id, Rate.user_id == current_user.id)
    result: Result = await db.execute(stmt_rate)
    rate = result.scalars().first()

    stmt_movie = select(Movie).where(Movie.id == movie_id)
    result: Result = await db.execute(stmt_movie)
    movie = result.scalars().first()

    if not rate:
        new_rate = Rate(rate=schema.score, user_id=current_user.id, movie_id=movie_id)
        movie.votes += 1
        db.add(new_rate)
        await db.commit()
        await db.refresh(new_rate)
        return {"message": f"new rate - {new_rate.rate}"}

    rate.rate = schema.score
    await db.commit()
    await db.refresh(rate)
    return {"message": f"updated rate - {rate.rate}"}


@router.post("/notification/{comment_id}/")
async def notification_comment(
        comment_id: int,
        schema: CommentSchema,
        current_user: UserModel = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
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
        message=f"{user.email} replied you"
    )

    db.add(new_notif)
    await db.commit()
    return {new_notif}
