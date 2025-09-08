from typing import List

from pydantic import BaseModel, ConfigDict


class GenreOut(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class MovieOut(BaseModel):
    title: str
    price: float
    genres: list[str]
    year: int

    model_config = ConfigDict(from_attributes=True)


class MovieListResponse(BaseModel):
    movies: List[MovieOut]

    model_config = ConfigDict(from_attributes=True)
