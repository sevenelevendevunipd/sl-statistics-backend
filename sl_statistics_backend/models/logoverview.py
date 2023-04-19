from pydantic import BaseModel


class MaxCountEntry(BaseModel):
    filename: str
    entry_count: int


class LogOverview(BaseModel):
    total_entries: int
    avg_entries: int
    max_count_entry: MaxCountEntry
    entries_std_dev: int

    class Config:
        json_encoders = {
            "datetime": lambda v: v.timedelta_isoformat(),
        }

    @staticmethod
    def empty() -> "LogOverview":
        return LogOverview(
            total_entries=0, avg_entries=0, entries_std_dev=0, max_count_entry=MaxCountEntry(filename="", entry_count=0)
        )
