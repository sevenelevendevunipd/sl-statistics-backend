from sl_parser import LogFile
from starlette.datastructures import FormData, UploadFile

from sl_statistics_backend import log_db
from sl_statistics_backend.log_database import LogDatabaseError
from sl_statistics_backend.models import StoredLogList
from sl_statistics_backend.schemas import LogDelete, LogUpload


async def delete_log_file(data: dict) -> int:
    delete_req = LogDelete(**data)
    return await log_db.delete_log(delete_req.log)


async def list_log_files() -> StoredLogList:
    return await log_db.uploaded_file_list


class LogUploadError(Exception):
    message: str

    def __init__(self, message: str, *args: object) -> None:
        super().__init__(*args)
        self.message = message


async def upload_log(form_data: FormData) -> int:
    form = LogUpload(**form_data)  # type: ignore
    log_file = form.log
    if not isinstance(log_file, UploadFile):
        raise LogUploadError("Everything is pretty fucked up.")
    if log_file.content_type not in {"text/csv", "application/vnd.ms-excel"}:
        raise LogUploadError("Invalid log file")
    if log_file.filename is None:
        raise LogUploadError("Missing log file name")
    content = await log_file.read()
    try:
        parsed_log = LogFile.parse_log(log_file.filename, content.decode("cp1252"))
    except Exception as e:
        raise LogUploadError(f"Log parsing error: {repr(e)[:64]}") from e
    try:
        return await log_db.upload(parsed_log)
    except LogDatabaseError as e:
        raise LogUploadError(e.message) from e
    except Exception as e:
        raise LogUploadError(f"Error while uploading to ElasticSearch: {repr(e)[:64]}") from e
