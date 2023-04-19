from pydantic import BaseModel


class CountResponse(BaseModel):
    count: int
