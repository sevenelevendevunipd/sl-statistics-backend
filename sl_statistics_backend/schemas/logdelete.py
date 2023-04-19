from pydantic import BaseModel


class LogDelete(BaseModel):
    log: str
