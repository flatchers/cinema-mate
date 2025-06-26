from sqlalchemy import Time, Float, Text, UniqueConstraint, CheckConstraint
from typing import List, Optional, TYPE_CHECKING
import uuid
from sqlalchemy import Integer, String, Table, Column, ForeignKey, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base


MovieGenreModel = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, nullable=False),
    )

MovieStarModel = Table(
    "movie_stars",
    Base.metadata,
    Column("star_id", ForeignKey("stars.id"), primary_key=True, nullable=False),
    Column("movie_id", ForeignKey("movies.id"), primary_key=True, nullable=False),
)

MovieDirectorModel = Table(
    "movie_directors",
    Base.metadata,
    Column("director_id", ForeignKey("directors.id"), primary_key=True, nullable=False),
    Column("movie_id", ForeignKey("movies.id"), primary_key=True, nullable=False),
)

MovieLikeUserModel = Table(
    "movie_like_users",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("movie_id", ForeignKey("movies.id"), primary_key=True, nullable=False),
)

MovieFavouriteUserModel = Table(
    "movie_favourite_users",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True, nullable=False),
    Column("movie_id", ForeignKey("movies.id"), primary_key=True, nullable=False),
)


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    movies: Mapped[List["Movie"]] = relationship(
        "Movie",
        secondary=MovieGenreModel,
        back_populates="genres",
    )


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    movies: Mapped[List["Movie"]] = relationship(
        "Movie",
        secondary=MovieStarModel,
        back_populates="stars"
    )


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    movies: Mapped[List["Movie"]] = relationship(
        "Movie",
        secondary=MovieDirectorModel,
        back_populates="directors"
    )


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    movies: Mapped[list["Movie"]] = relationship("Movie", back_populates="certification")


class Comment(Base):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="comments")
    movie_id = mapped_column(ForeignKey("movies.id"))
    movie: Mapped["Movie"] = relationship("Movie", back_populates="comments")


class Rate(Base):
    __tablename__ = "rate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rate: Mapped[int] = mapped_column(Float, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="rates")
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    movie: Mapped["Movie"] = relationship("Movie", back_populates="rates")

    __table_args__ = (
        CheckConstraint("rate >= 1.0 AND rate <= 10.0", name="rate_between_1_and_10"),
    )


if TYPE_CHECKING:
    from src.database.models.accounts import UserModel


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[float] = mapped_column(Float, nullable=True)
    gross: Mapped[float] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2))
    comments: Mapped[Optional[List[Comment]]] = relationship(
        "Comment",
        back_populates="movie"
    )
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    like_users: Mapped[Optional[List["UserModel"]]] = relationship(
        "UserModel",
        secondary=MovieLikeUserModel,
        back_populates="like_movies"
    )
    favourite_users: Mapped[Optional[List["UserModel"]]] = relationship(
        "UserModel",
        secondary=MovieFavouriteUserModel,
        back_populates="favourite_movies"
    )
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id", ondelete="CASCADE"), nullable=False)
    certification: Mapped[Certification] = relationship("Certification", back_populates="movies")
    genres: Mapped[list[Genre]] = relationship(
        "Genre",
        secondary=MovieGenreModel,
        back_populates="movies"
    )
    directors: Mapped[list[Director]] = relationship(
        "Director",
        secondary=MovieDirectorModel,
        back_populates="movies"
    )
    stars: Mapped[list[Star]] = relationship(
        "Star",
        secondary=MovieStarModel,
        back_populates="movies"
    )
    rates: Mapped[list[Rate]] = relationship(
        "Rate",
        back_populates="movie"
    )

    __table_args__ = (
        UniqueConstraint("name", "year", "time"),
    )
