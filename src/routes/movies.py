from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, Result, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from src.database.models.accounts import UserModel, UserGroupEnum, UserGroup
from src.database.models.movies import Movie, Certification, Genre, Director, Star
from src.database.session_sqlite import get_db
from src.schemas.movies import MovieCreateSchema, MoviesPaginationResponse, MovieList, MovieCreateResponse
from src.security.token_manipulation import get_current_user

router = APIRouter()


""" CRUD OPERATIONS FOR MODERATORS """


@router.post("/create/", response_model=MovieCreateResponse, status_code=status.HTTP_201_CREATED)
async def film_create(
        schema: MovieCreateSchema,
        db: AsyncSession = Depends(get_db),

):

    stmt_group = select(UserGroup).where(UserGroup.name == UserGroupEnum.MODERATOR)
    result_group = await db.execute(stmt_group)
    user_group = result_group.scalars().first()

    if user_group.name != UserGroupEnum.MODERATOR:
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


@router.get("/lists/", response_model=MoviesPaginationResponse, status_code=status.HTTP_200_OK)
async def movie_list(
        page: int = Query(1, ge=1),
        per_page: int = Query(10, ge=1),
        db: AsyncSession = Depends(get_db)
):

    stmt = select(Movie).order_by(Movie.id.desc())
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
