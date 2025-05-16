from typing import List, Optional

from pydantic import BaseModel


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


class GenreResponse(BaseModel):
    name: str


class DirectorResponse(BaseModel):
    name: str


class StarResponse(BaseModel):
    name: str


class MovieCreateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    year: int
    certification: str
    genres: list[str]
    directors: list[str]
    stars: list[str]


class MovieCreateSchema(BaseModel):
    name: str
    year: int
    time: int
    imdb: float
    votes: int
    meta_score: float
    gross: float
    description: str
    price: float
    certification: str
    genres: list[str]
    directors: list[str]
    stars: list[str]
