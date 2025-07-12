from typing import List, Optional

from pydantic import BaseModel, Field

from src.database.models.movies import Comment
from src.schemas.accounts import UserCreate


class MovieList(BaseModel):
    id: int
    name: str
    year: int
    time: int
    imdb: float
    price: float

    model_config = {"from_attributes": True}


class MoviesPaginationResponse(BaseModel):
    movies: list[MovieList]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


class CertificationResponse(BaseModel):
    name: str

    class Config:
        from_attributes: bool = True


class GenreResponse(BaseModel):
    name: str

    class Config:
        from_attributes: bool = True


class DirectorResponse(BaseModel):
    name: str

    class Config:
        from_attributes: bool = True


class StarResponse(BaseModel):
    name: str

    class Config:
        from_attributes: bool = True


class CommentResponse(BaseModel):
    user: UserCreate
    comment: str

    class Config:
        from_attributes: bool = True


class MovieCreateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    year: int
    certification: str
    genres: list[str]
    directors: list[str]
    stars: list[str]

    class Config:
        from_attributes: bool = True


class MovieCreateSchema(BaseModel):
    name: Optional[str] = Field(None)
    year: Optional[int] = Field(None)
    time: Optional[int] = Field(None)
    imdb: Optional[float] = Field(None)
    votes: Optional[int] = Field(None)
    meta_score: Optional[float] = Field(None)
    gross: Optional[float] = Field(None)
    description: Optional[str] = Field(None)
    price: Optional[float] = Field(None)
    certification: Optional[str] = Field(None)
    genres: Optional[list[str]] = Field(None)
    directors: Optional[list[str]] = Field(None)
    stars: Optional[list[str]] = Field(None)

    class Config:
        from_attributes: bool = True


class MovieDetailResponse(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: float
    gross: float
    description: str
    price: float
    like_count: int
    certification: CertificationResponse
    genres: List[GenreResponse]
    directors: List[DirectorResponse]
    stars: List[StarResponse]
    comments: List[CommentResponse]

    class Config:
        from_attributes: bool = True


class CommentSchema(BaseModel):
    comments: str

    class Config:
        from_attributes: bool = True


class MoviesForGenreResponse(BaseModel):
    count_movies: int
    genres: List[GenreResponse]
    movies: List[MovieList]

    class Config:
        from_attributes: bool = True


class ScoreRequestSchema(BaseModel):
    score: float


class MovieUpdate(BaseModel):
    name: str = None
    year: int = None
    time: int = None
    imdb: float = None
    votes: int = None
    meta_score: float = None
    gross: float = None
    description: str = None
    price: float = None

    class Config:
        from_attributes: bool = True
