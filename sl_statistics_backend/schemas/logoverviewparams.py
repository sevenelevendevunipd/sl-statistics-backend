from datetime import datetime

from pydantic import BaseModel


class LogOverviewParams(BaseModel):
    start: datetime
    end: datetime
