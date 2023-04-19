from pydantic import BaseModel


class LogFrequencyEntry(BaseModel):
    firmware: str
    event_code: str
    count: int
