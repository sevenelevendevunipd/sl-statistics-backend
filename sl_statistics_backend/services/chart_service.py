from starlette.datastructures import QueryParams

from sl_statistics_backend import log_db
from sl_statistics_backend.models import ChartFilterData, HistogramEntry
from sl_statistics_backend.schemas import FirmwareChartParams, LogOverviewParams, TimeChartParams


async def get_chart_filter_data(qp: QueryParams) -> ChartFilterData:
    params = LogOverviewParams(**qp)  # type: ignore
    return await log_db.chart_filters(params.start, params.end)


async def get_firmware_chart_data(data: dict) -> list[HistogramEntry]:
    params = FirmwareChartParams(**data)
    return await log_db.firmware_chart_data(params.start, params.end, params.selected_firmwares, params.selected_codes)


async def get_time_chart_data(data: dict) -> list[HistogramEntry]:
    params = TimeChartParams(**data)
    return await log_db.time_chart_data(params.start, params.end, params.selected_subunits, params.selected_codes)
