from pathlib import Path
import pytest
import asyncio
from sl_statistics_backend.log_database import LogDatabase, LogDatabaseError
from starlette.testclient import TestClient
from sl_statistics_backend import app
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from elasticsearch import AsyncElasticsearch
from sl_statistics_backend.log_database import LogDatabase
from sl_parser import LogFile
from sl_statistics_backend.models import StoredLogFile, StoredLogList
from datetime import datetime
from sl_statistics_backend.__init__ import list_logs



client = TestClient(app)

class Test_upload_log:

    async def mock_upload(self, log_file):
        return 11

    # Simulate uploading of a valid file
    @patch.object(LogDatabase, "upload", mock_upload)
    def test_upload_log_valid_log(self):
        

        response = client.put("/api/log", files={"log": ("log.csv", Path(__file__).with_name("log.csv").read_text(), "text/csv")})

        assert response.status_code == 200
        assert response.json() == {"count": 11}
    
    # Simulate uploading an invalid file (not a CSV)

    @patch.object(LogDatabase, "upload", mock_upload)
    def test_upload_log_invalid_file(self):
        response = client.put("/api/log", files={"log": ("rowWrong.csv", "random invalid data")})
        assert response.status_code == 400
        assert response.json() == {"errors": ["Invalid log file"]}


    #simulate parsing error

    def test_upload_parse_error(self):
        response = client.put("/api/log", files={"log": ("logErr.csv", Path(__file__).with_name("logErr.csv").read_text(), "text/csv")})
        assert response.status_code == 400


    # Simulate uploading of an existing file (duplicate)

    async def mock_upload_DB_error(self, log_file):
        raise LogDatabaseError("Log file already uploaded!")

    @patch.object(LogDatabase, "upload", mock_upload_DB_error)
    def test_upload_log_error(self):
        response = client.put("/api/log", files={"log": ("log.csv", Path(__file__).with_name("log.csv").read_text(), "text/csv")})
        assert response.status_code == 400
        assert response.json() == {"errors": ["Log file already uploaded!"]}

    # Simulate generic error

    async def mock_upload_exception(self, log_file):
        raise TypeError

    @patch.object(LogDatabase, "upload", mock_upload_exception)
    def test_upload_error(self):
        response = client.put("/api/log", files={"log": ("log.csv", Path(__file__).with_name("log.csv").read_text(), "text/csv")})
        assert response.status_code == 400

    # # Simulate missing file
    # @patch.object(LogDatabase, "upload", mock_upload)
    # def test_upload_missing(self):

    #     print("cacca")
    #     print(response.text)
    #     # verifica che la risposta del server sia conforme alle aspettative
    #     assert response.status_code == 400
    #     assert response.json() == {"errors": ["Missing log file name"]}


async def mock_uploaded_file_list(self):
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
    return StoredLogList(log_files=log_files, min_timestamp=min_timestamp, max_timestamp=max_timestamp)


@patch.object(LogDatabase, "uploaded_file_list", mock_uploaded_file_list, new_callable=PropertyMock)
def test_list_logs():
    response = client.get("/api/log_list")
    assert response.status_code == HTTPStatus.OK
    assert response.headers["Content-Type"] == "application/json"
    expected_response = mock_uploaded_file_list().json()
    assert response.json() == expected_response


# simulating a delete in db

# async def mock_delete_log(self, log):
#     return 11

# @patch.object(LogDatabase, "delete_log", mock_delete_log)
# def test_delete_log():
#     # response1 = client.put("/api/log", files={"log": ("log.csv", Path(__file__).with_name("log.csv").read_text(), "text/csv")})
#     response2 = client.delete("/api/log",  json={"log": "log.csv"})
#     print(response.text)
#     # assert response.status_code == 200
#     # assert isinstance(response.json(), list)
        





