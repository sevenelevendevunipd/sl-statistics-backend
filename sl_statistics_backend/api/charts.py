from spectree import Response as SpectreeResponse
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from sl_statistics_backend import spec
from sl_statistics_backend.models import ChartFilterData
from sl_statistics_backend.schemas import (
    FirmwareChartParams,
    Histogram,
    LogOverviewParams,
    TimeChartParams,
)
from sl_statistics_backend.services import chart_service


@spec.validate(query=LogOverviewParams, resp=SpectreeResponse(HTTP_200=ChartFilterData), tags=["Charts"])
async def chart_filters(request: Request) -> Response:
    filter_data = await chart_service.get_chart_filter_data(request.query_params)
    return JSONResponse(filter_data.dict())


@spec.validate(json=FirmwareChartParams, resp=SpectreeResponse(HTTP_200=Histogram), tags=["Charts"])
async def firmware_chart(request: Request) -> Response:
    chart_bars = await chart_service.get_firmware_chart_data(await request.json())
    return JSONResponse(Histogram(bars=chart_bars).dict())


@spec.validate(json=TimeChartParams, resp=SpectreeResponse(HTTP_200=Histogram), tags=["Charts"])
async def time_chart(request: Request) -> Response:
    chart_bars = await chart_service.get_time_chart_data(await request.json())
    return JSONResponse(Histogram(bars=chart_bars).dict())


ChartMount = Mount(
    "/charts",
    routes=[
        Route("/filters", chart_filters),
        Route("/time", time_chart, methods=["POST"]),  # should be GET but args don't fit in QS
        Route("/firmware", firmware_chart, methods=["POST"]),  # should be GET but args don't fit in QS
    ],
)
