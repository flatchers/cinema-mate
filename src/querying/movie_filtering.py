from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter

from src.database.models import Movie


class MovieFilter(Filter):
    year: Optional[int] = None
    imdb: Optional[int] = None

    class Constants(Filter.Constants):
        model = Movie
