from datetime import datetime, time

from sqlalchemy import Time, Float, Text, UniqueConstraint
from typing import List

import uuid
from sqlalchemy import Integer, String, Table, Column, ForeignKey, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

MovieGenreModel = Table(
    "movie_genres",
    Base.metadata,
    Column("genre_id", ForeignKey("genres.id"), primary_key=True, nullable=False),
    Column("movie_id", ForeignKey("movies.id"), primary_key=True, nullable=False),
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


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    movies: Mapped[List["Movie"]] = relationship(
        "Movie",
        secondary=MovieGenreModel,
        back_populates="genre"
    )


class Star(Base):
    __tablename__ = "stars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    movies: Mapped[List["Movie"]] = relationship(
        "Movie",
        secondary=MovieStarModel,
        back_populates="star"
    )


class Director(Base):
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    movies: Mapped[List["Movie"]] = relationship(
        "Movie",
        secondary=MovieDirectorModel,
        back_populates="director"
    )


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    movies: Mapped[list["Movie"]] = relationship("Movie", back_populates="certification")


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[uuid.UUID] = mapped_column(unique=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    time: Mapped[int] = mapped_column(Integer, nullable=False)
    imdb: Mapped[float] = mapped_column(Float, nullable=False)
    votes: Mapped[int] = mapped_column(Integer, nullable=False)
    meta_score: Mapped[float] = mapped_column(Float, nullable=True)
    gross: Mapped[float] = mapped_column(Float, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(10, 2))
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id", ondelete="CASCADE"), nullable=False)
    certification: Mapped[Certification] = relationship("Certification", back_populates="movies")
    genres: Mapped[list[Genre]] = relationship("Genre", back_populates="movies")
    directors: Mapped[list[Director]] = relationship("Director", back_populates="movies")
    stars: Mapped[list[Star]] = relationship("Star", back_populates="movies")
    __table_args__ = (
        UniqueConstraint("name", "year", "time"),
    )
