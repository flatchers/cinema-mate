from typing import List, Optional

from pydantic import BaseModel


class MovieList(BaseModel):
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
    genres: List[str]
    directors: List[str]
    stars: List[str]


class MoviesPaginationResponse(MovieList):
    movies: list[MovieList]
    prev_page: Optional[str]
    next_page: Optional[str]
    total_pages: int
    total_items: int


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
    genres: List[str]
    directors: List[str]
    stars: List[str]


