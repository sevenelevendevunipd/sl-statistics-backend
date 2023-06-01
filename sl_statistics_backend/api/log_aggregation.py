from spectree import Response as SpectreeResponse
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from sl_statistics_backend import spec
from sl_statistics_backend.models import LogOverview
from sl_statistics_backend.schemas import (
    LogFrequency,
    LogFrequencyParams,
    LogOverviewParams,
)
from sl_statistics_backend.services import log_aggregation_service


@spec.validate(query=LogOverviewParams, resp=SpectreeResponse(HTTP_200=LogOverview), tags=["Log aggregation analysis"])
async def selected_logs_overview(request: Request) -> Response:
    overview = await log_aggregation_service.selected_log_overview(request.query_params)
    return Response(
        overview.json(),
        media_type="application/json",
    )


@spec.validate(json=LogFrequencyParams, resp=SpectreeResponse(HTTP_200=LogFrequency), tags=["Log aggregation analysis"])
async def log_frequency(request: Request) -> Response:
    frequency_data = await log_aggregation_service.log_frequency_analysis(await request.json())
    return JSONResponse(LogFrequency(entries=frequency_data).dict())


LogAggregationMount = Mount(
    "/aggregation",
    routes=[
        Route("/overview", selected_logs_overview),
        Route("/frequency", log_frequency, methods=["POST"]),  # should be GET but args don't fit in QS
    ],
)
