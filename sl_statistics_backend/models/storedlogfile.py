from datetime import datetime

from pydantic import BaseModel


class StoredLogFile(BaseModel):
    file_name: str
    first_entry_timestamp: datetime
    last_entry_timestamp: datetime
    entry_count: int

    class Config:
        json_encoders = {
            "datetime": lambda v: v.timedelta_isoformat(),
        }
