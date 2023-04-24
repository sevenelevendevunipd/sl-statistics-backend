from pydantic import BaseModel


class ChartFilterData(BaseModel):
    subunits: list[int]
    codes: list[str]
    firmwares: list[str]
