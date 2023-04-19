from datetime import datetime

from pydantic import BaseModel

from .storedlogfile import StoredLogFile


class StoredLogList(BaseModel):
    log_files: list[StoredLogFile]
    min_timestamp: datetime
    max_timestamp: datetime
