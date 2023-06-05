from starlette.datastructures import QueryParams

from sl_statistics_backend import log_db
from sl_statistics_backend.models import LogFrequencyEntry, LogOverview
from sl_statistics_backend.schemas import LogFrequencyParams, LogOverviewParams


async def selected_log_overview(qp: QueryParams) -> LogOverview:
    params = LogOverviewParams(**qp)  # type: ignore
    return await log_db.log_overview(params.start, params.end)


async def log_frequency_analysis(data: dict) -> list[LogFrequencyEntry]:
    params = LogFrequencyParams(**data)
    return await log_db.log_entries_frequency(params.start, params.end, params.selected_subunits)
