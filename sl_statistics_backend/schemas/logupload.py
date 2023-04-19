from pydantic import BaseModel
from spectree import BaseFile


class LogUpload(BaseModel):
    log: BaseFile
