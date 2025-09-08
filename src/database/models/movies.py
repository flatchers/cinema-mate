from datetime import datetime

from sqlalchemy import Float, Text, UniqueConstraint, CheckConstraint, func
from typing import List, Optional, TYPE_CHECKING
import uuid
from sqlalchemy import Integer, String, Table, Column, ForeignKey, DECIMAL
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base
from src.database.models.shopping_cart import CartItemsModel

MovieGenreModel = Table(
    "movie_genres",
    Base.metadata,
    Column(
        "movie_id",
        ForeignKey("movies.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "genre_id",
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    extend_existing=True,
)

MovieStarModel = Table(
    "movie_stars",
    Base.metadata,
    Column(
        "star_id",
        ForeignKey("stars.id"),
        primary_key=True,
        nullable=False
    ),
    Column(
        "movie_id",
        ForeignKey("movies.id"),
        primary_key=True,
        nullable=False
    ),
    extend_existing=True,
)

MovieDirectorModel = Table(
    "movie_directors",
    Base.metadata,
    Column(
        "director_id",
        ForeignKey("directors.id"),
        primary_key=True,
        nullable=False
    ),
    Column(
        "movie_id",
        ForeignKey("movies.id"),
        primary_key=True,
        nullable=False
    ),
    extend_existing=True,
)

MovieLikeUserModel = Table(
    "movie_like_users",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column(
        "movie_id",
        ForeignKey("movies.id"),
        primary_key=True,
        nullable=False
    ),
    extend_existing=True,
)

MovieFavouriteUserModel = Table(
    "movie_favourite_users",
    Base.metadata,
    Column(
        "user_id",
        ForeignKey("users.id"),
        primary_key=True,
        nullable=False
    ),
    Column(
        "movie_id",
        ForeignKey("movies.id"),
        primary_key=True,
        nullable=False
    ),
    extend_existing=True,
)


class Genre(Base):
    __tablename__ = "genres"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    movies: Mapped[List["Movie"]] = relationship(
        "Movie",
        secondary=MovieGenreModel,
        back_populates="genres",
    )


class Star(Base):
    __tablename__ = "stars"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    movies: Mapped[List["Movie"]] = relationship(
        "Movie", secondary=MovieStarModel, back_populates="stars"
    )


class Director(Base):
    __tablename__ = "directors"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    movies: Mapped[List["Movie"]] = relationship(
        "Movie", secondary=MovieDirectorModel, back_populates="directors"
    )


class Certification(Base):
    __tablename__ = "certifications"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    movies: Mapped[list["Movie"]] = relationship(
        "Movie", back_populates="certification"
    )


class Comment(Base):
    __tablename__ = "comment"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    comment: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="comments"
    )
    movie_id = mapped_column(ForeignKey("movies.id"))
    movie: Mapped["Movie"] = relationship("Movie", back_populates="comments")
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="comment"
    )


class Rate(Base):
    __tablename__ = "rate"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    rate: Mapped[int] = mapped_column(Float, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["UserModel"] = relationship(
        "UserModel",
        back_populates="rates"
    )
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"))
    movie: Mapped["Movie"] = relationship("Movie", back_populates="rates")

    __table_args__ = (
        CheckConstraint(
            "rate >= 1.0 AND rate <= 10.0",
            name="rate_between_1_and_10"
        ),
        {"extend_existing": True},
    )


if TYPE_CHECKING:
    from src.database.models.accounts import UserModel
    from src.database.models.order import OrderItemModel


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    uuid: Mapped[str] = mapped_column(
        String(36), unique=True, default=lambda: str(uuid.uuid4())
    )
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
        "Comment", back_populates="movie"
    )
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    like_users: Mapped[Optional[List["UserModel"]]] = relationship(
        "UserModel", secondary=MovieLikeUserModel, back_populates="like_movies"
    )
    favourite_users: Mapped[Optional[List["UserModel"]]] = relationship(
        "UserModel",
        secondary=MovieFavouriteUserModel,
        back_populates="favourite_movies",
    )
    certification_id: Mapped[int] = mapped_column(
        ForeignKey("certifications.id", ondelete="CASCADE"), nullable=False
    )
    certification: Mapped[Certification] = relationship(
        "Certification", back_populates="movies"
    )
    genres: Mapped[list[Genre]] = relationship(
        "Genre", secondary=MovieGenreModel, back_populates="movies"
    )
    directors: Mapped[list[Director]] = relationship(
        "Director", secondary=MovieDirectorModel, back_populates="movies"
    )
    stars: Mapped[list[Star]] = relationship(
        "Star", secondary=MovieStarModel, back_populates="movies"
    )
    rates: Mapped[list[Rate]] = relationship("Rate", back_populates="movie")
    cart_items: Mapped[list["CartItemsModel"]] = relationship(
        "CartItemsModel", back_populates="movie"
    )
    order_items: Mapped[list["OrderItemModel"]] = relationship(
        "OrderItemModel", back_populates="movie"
    )

    __table_args__ = (
        UniqueConstraint("name", "year", "time"),
        {"extend_existing": True},
    )


class Notification(Base):
    __tablename__ = "notification"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    comment_id: Mapped[int] = mapped_column(
        ForeignKey("comment.id", ondelete="CASCADE"), nullable=True
    )
    message: Mapped[str] = mapped_column()
    is_read: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    user: Mapped["UserModel"] = relationship(
        "UserModel", back_populates="notifications"
    )
    comment: Mapped["Comment"] = relationship(
        "Comment",
        back_populates="notifications"
    )
