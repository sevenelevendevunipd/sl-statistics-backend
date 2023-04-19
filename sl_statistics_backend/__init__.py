import contextlib
from collections.abc import AsyncGenerator

from sl_parser import LogFile
from spectree import Response as SpectreeResponse
from spectree import SpecTree
from starlette.applications import Starlette
from starlette.datastructures import UploadFile
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from . import config
from .log_database import LogDatabase, LogDatabaseError
from .models import LogOverview, StoredLogList
from .schemas import (
    CountResponse,
    ErrorResponse,
    LogDelete,
    LogFrequency,
    LogFrequencyParams,
    LogOverviewParams,
    LogUpload,
)

spec = SpecTree("starlette")
log_db = LogDatabase(str(config.ELASTICSEARCH_URL))


@spec.validate(
    form=LogUpload,
    resp=SpectreeResponse(HTTP_200=CountResponse, HTTP_400=ErrorResponse),
)
async def upload_log(request: Request) -> Response:
    form = LogUpload(**(await request.form()))  # type: ignore
    log_file = form.log
    if not isinstance(log_file, UploadFile) or log_file.content_type != "text/csv":
        return JSONResponse({"errors": ["Invalid log file"]}, status_code=400)
    if log_file.filename is None:
        return JSONResponse({"errors": ["Missing log file name"]}, status_code=400)
    content = await log_file.read()
    try:
        parsed_log = LogFile.parse_log(log_file.filename, content.decode("cp1252"))
    except Exception as e:
        return JSONResponse({"errors": [f"Log parsing error: {repr(e)[:64]}"]}, status_code=400)
    try:
        count = await log_db.upload(parsed_log)
        return JSONResponse({"count": count})
    except LogDatabaseError as e:
        return JSONResponse({"errors": [e.message]}, status_code=400)
    except Exception as e:
        return JSONResponse(
            {"errors": [f"Error while uploading to ElasticSearch: {repr(e)[:64]}"]},
            status_code=400,
        )


@spec.validate(resp=SpectreeResponse(HTTP_200=StoredLogList))
async def list_logs(request: Request) -> Response:
    return Response(
        (await log_db.uploaded_file_list).json(),
        media_type="application/json",
    )


@spec.validate(json=LogDelete, resp=SpectreeResponse(HTTP_200=CountResponse))
async def delete_log(request: Request) -> Response:
    data = LogDelete(**await request.json())
    deleted_entries = await log_db.delete_log(data.log)
    return JSONResponse({"count": deleted_entries})


@spec.validate(query=LogOverviewParams, resp=SpectreeResponse(HTTP_200=LogOverview))
async def selected_logs_overview(request: Request) -> Response:
    params = LogOverviewParams(**request.query_params)  # type: ignore
    data = await log_db.log_overview(params.start, params.end)
    return Response(
        data.json(),
        media_type="application/json",
    )


@spec.validate(json=LogFrequencyParams, resp=SpectreeResponse(HTTP_200=LogFrequency))
async def log_frequency(request: Request) -> Response:
    params = LogFrequencyParams(**await request.json())  # type: ignore
    data = await log_db.log_entries_frequency(params.start, params.end, params.selected_subunits)
    return JSONResponse(LogFrequency(entries=data).dict())


@contextlib.asynccontextmanager
async def app_lifespan(app: Starlette) -> AsyncGenerator:
    yield
    await log_db.close()


app = Starlette(
    debug=config.DEBUG,
    routes=[
        Mount(
            "/api",
            routes=[
                Route("/log", upload_log, methods=["PUT"]),
                Route("/log", delete_log, methods=["DELETE"]),
                Route("/log_list", list_logs),
                Route("/overview", selected_logs_overview),
                Route(
                    "/frequency", log_frequency, methods=["POST"]
                ),  # should be GET, but if using GET+qs params requests are too big
            ],
        ),
    ],
    lifespan=app_lifespan,
)

if config.DISABLE_CORS:
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"])

spec.register(app)
