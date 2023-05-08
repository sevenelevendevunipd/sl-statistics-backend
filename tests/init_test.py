# ruff: noqa: ANN101, PLR2004

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from sl_parser import LogFile
from starlette.testclient import TestClient

from sl_statistics_backend import app
from sl_statistics_backend.log_database import LogDatabase, LogDatabaseError
from sl_statistics_backend.models import StoredLogFile, StoredLogList

client = TestClient(app)


class TestUploadLog:
    # Simulate uploading of a valid file
    @patch.object(LogDatabase, "upload", return_value=11)
    def test_upload_log_valid_log(self, _: LogFile) -> None:
        response = client.put(
            "/api/log", files={"log": ("log.csv", Path(__file__).with_name("log.csv").read_text(), "text/csv")}
        )

        assert response.status_code == 200
        assert response.json() == {"count": 11}

    # Simulate uploading an invalid file (not a CSV)
    def test_upload_log_invalid_file(self) -> None:
        response = client.put("/api/log", files={"log": ("rowWrong.csv", "random invalid data", "random/mime")})
        assert response.status_code == 400
        assert response.json() == {"errors": ["Invalid log file"]}

    # simulate parsing error

    def test_upload_parse_error(self) -> None:
        response = client.put(
            "/api/log", files={"log": ("logErr.csv", Path(__file__).with_name("logErr.csv").read_text(), "text/csv")}
        )
        assert response.status_code == 400
        assert "Log parsing error" in response.text

    # Simulate uploading of an existing file (duplicate)

    async def mock_upload_duplicate_error(self, _: LogFile) -> None:
        raise LogDatabaseError("Log file already uploaded!")

    @patch.object(LogDatabase, "upload", mock_upload_duplicate_error)
    def test_upload_log_error(self) -> None:
        response = client.put(
            "/api/log", files={"log": ("log.csv", Path(__file__).with_name("log.csv").read_text(), "text/csv")}
        )
        assert response.status_code == 400
        assert response.json() == {"errors": ["Log file already uploaded!"]}

    # Simulate generic error

    async def mock_upload_exception(self, _: LogFile) -> None:
        raise TypeError

    @patch.object(LogDatabase, "upload", mock_upload_exception)
    def test_upload_error(self) -> None:
        response = client.put(
            "/api/log", files={"log": ("log.csv", Path(__file__).with_name("log.csv").read_text(), "text/csv")}
        )
        assert response.status_code == 400


log_files = [
    StoredLogFile(
        file_name="log_file_1",
        first_entry_timestamp=datetime(2023, 5, 1, 0, 0),
        last_entry_timestamp=datetime(2023, 5, 1, 12, 0),
        entry_count=1000,
    ),
    StoredLogFile(
        file_name="log_file_2",
        first_entry_timestamp=datetime(2023, 5, 2, 0, 0),
        last_entry_timestamp=datetime(2023, 5, 2, 12, 0),
        entry_count=500,
    ),
]
min_timestamp = datetime(2023, 5, 1, 0, 0)
max_timestamp = datetime(2023, 5, 2, 12, 0)
log_list = StoredLogList(log_files=log_files, min_timestamp=min_timestamp, max_timestamp=max_timestamp)


@property
async def mock_uploaded_file_list(_: StoredLogList) -> StoredLogList:
    return log_list


@patch.object(LogDatabase, "uploaded_file_list", mock_uploaded_file_list)
def test_list_logs() -> None:
    response = client.get("/api/log_list")
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    expected_response = json.loads(log_list.json())
    assert response.json() == expected_response
