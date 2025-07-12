from typing import List

from pydantic import BaseModel

from src.database.models.movies import Genre


class GenreOut(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class MovieOut(BaseModel):
    title: str
    price: float
    genres: list[str]
    year: int

    class Config:
        from_attributes = True


class MovieListResponse(BaseModel):
    movies: List[MovieOut]

    class Config:
        from_attributes = True

