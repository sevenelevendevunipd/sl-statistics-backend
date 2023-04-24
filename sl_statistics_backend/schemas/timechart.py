from pydantic import BaseModel

from sl_statistics_backend.models import TimeChartEntry


class TimeChart(BaseModel):
    bars: list[TimeChartEntry]
