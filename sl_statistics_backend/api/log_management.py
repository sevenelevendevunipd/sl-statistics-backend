from spectree import Response as SpectreeResponse
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from sl_statistics_backend import spec
from sl_statistics_backend.models import StoredLogList
from sl_statistics_backend.schemas import (
    CountResponse,
    ErrorResponse,
    LogDelete,
    LogUpload,
)
from sl_statistics_backend.services import log_management_service
from sl_statistics_backend.services.log_management_service import LogUploadError


@spec.validate(
    form=LogUpload, resp=SpectreeResponse(HTTP_200=CountResponse, HTTP_400=ErrorResponse), tags=["Log file management"]
)
async def upload_log(request: Request) -> Response:
    form_data = await request.form()
    try:
        count = await log_management_service.upload_log(form_data)
        return JSONResponse({"count": count})
    except LogUploadError as e:
        return JSONResponse({"errors": [e.message]}, status_code=400)


@spec.validate(resp=SpectreeResponse(HTTP_200=StoredLogList), tags=["Log file management"])
async def list_logs(_: Request) -> Response:
    return Response((await log_management_service.list_log_files()).json(), media_type="application/json")


@spec.validate(json=LogDelete, resp=SpectreeResponse(HTTP_200=CountResponse), tags=["Log file management"])
async def delete_log(request: Request) -> Response:
    data = await request.json()
    count = await log_management_service.delete_log_file(data)
    return JSONResponse({"count": count})


LogManagementMount = Mount(
    "",
    routes=[
        Route("/log", upload_log, methods=["PUT"]),
        Route("/log", delete_log, methods=["DELETE"]),
        Route("/log_list", list_logs),
    ],
)
