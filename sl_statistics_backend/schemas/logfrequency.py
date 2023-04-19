from pydantic import BaseModel

from sl_statistics_backend.models import LogFrequencyEntry


class LogFrequency(BaseModel):
    entries: list[LogFrequencyEntry]
