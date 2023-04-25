from pydantic import BaseModel

from sl_statistics_backend.models import HistogramEntry


class Histogram(BaseModel):
    bars: list[HistogramEntry]
