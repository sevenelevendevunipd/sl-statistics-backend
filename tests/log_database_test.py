from datetime import datetime
from typing import Any

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import asyncio
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk
from elasticsearch.exceptions import NotFoundError
from elasticsearch.helpers import BulkIndexError
from sl_parser import LogFile

from sl_statistics_backend.log_database import LogDatabase, LogDatabaseError
from sl_statistics_backend.models import (
    LogOverview,
    StoredLogFile,
    StoredLogList,
)

mock_elastic = AsyncMock()

@pytest.fixture(scope="function")
def log_database() -> LogDatabase:
    index_name = "test_smartlog"
    log_db = LogDatabase(mock_elastic, index_name)
    return log_db

@pytest.fixture(scope="function")
def log_file() -> LogFile:
    entries = [{
            "timestamp": "2023-05-05T14:30:00.123000",
            "code": "AplCmdErrorUnitSubunit",
            "description": "AplCmdErrorUnitSubunit",
            "file": "test.log",
            "ini_filename": "MAPK_Unit_v2_02_00.ini",
            "subunit": 0,
            "type_um": "Hex",
            "unit": 1,
            "unit_subunit_id": 0,
            "value": "0x0000",
            "snapshot": "0",
            "color": "0xFFADFF2F",
        }]
    pcDatetime = datetime.now()
    upsDatetime = datetime.now()
    unitsSubunits = {
                1: {
                    "ini_file": "firmware1",
                    "subunits": {
                        1: 'subunit1', 
                        2: 'subunit2'
                }}}

    log_file = LogFile(filename="test.log", pc_datetime=pcDatetime, ups_datetime=upsDatetime, 
                        units_subunits=unitsSubunits, log_entries=entries)
    
    return log_file

@pytest.mark.asyncio
async def test_upload(log_database: LogDatabase, log_file: LogFile) -> None:
    # Test uploading a log file
    with patch.object(log_database, '_log_already_uploaded', return_value=False):
        with patch.object(log_database, '_call_async_bulk', return_value=(1,0)):
            result = await log_database.upload(log_file)
            assert result == 1

    # Test that an exception is raised if the log file was already uploaded
    with pytest.raises(LogDatabaseError):
        await log_database.upload(log_file)

@pytest.mark.asyncio
async def test_uploaded_file_list(log_database: LogDatabase) -> None:
    #quando viene fatto il mock di elasticsearch viene restituita log_files vuota e il primo datetime possibile,
    #a meno che non gli venga esplicitamente detto di restituire qualcos'altro ma nel nostro caso non serve.
    expected_result = StoredLogList(
        log_files=[],
        min_timestamp=datetime(1970, 1, 1, 1, 0, 1),
        max_timestamp=datetime(1970, 1, 1, 1, 0, 1),
    )

    # Test getting the list of uploaded log files 
    result = await log_database.uploaded_file_list
    print(result)
    assert result == expected_result

@pytest.mark.asyncio
async def test_composite_paginate(log_database: LogDatabase) -> None:
    mock_elastic.search = AsyncMock(side_effect=[
                        {
                            "aggregations": {
                                "agg": {
                                    "buckets": [
                                        {"key": "value1", "doc_count": 10},
                                        {"key": "value2", "doc_count": 5},
                                        {"key": "value3", "doc_count": 2},
                                    ],
                                    "after_key": "value3"
                                }
                            }
                        },
                        {
                            "aggregations": {
                                "agg": {
                                    "buckets": [
                                        {"key": "value4", "doc_count": 7},
                                        {"key": "value5", "doc_count": 3},
                                    ],
                                }
                            }
                        }
                    ])
    result = await log_database._composite_paginate("my_index", {"composite": {"sources": [{"field": "my_field"}]}})
    assert result == [
                        {"key": "value1", "doc_count": 10},
                        {"key": "value2", "doc_count": 5},
                        {"key": "value3", "doc_count": 2},
                        {"key": "value4", "doc_count": 7},
                        {"key": "value5", "doc_count": 3},
                    ]


@pytest.mark.asyncio
async def test_close(log_database: LogDatabase) -> None:
    mock_elastic.close.assert_not_called()
    await log_database.close()
    mock_elastic.close.assert_called_once()

@pytest.mark.asyncio
async def test_delete_log(log_database: LogDatabase) -> None:
    mock_elastic.delete_by_query.return_value = {"total": 1}
    result = await log_database.delete_log("test.log")
    assert result == 1

# @pytest.mark.asyncio
# async def test_log_overview(log_database: LogDatabase) -> None:
#     mock_elastic.search.return_value = {
#                             "hits": {"total": {"value": 1}},
#                             "aggregations": {
#                                 "file": {
#                                     "buckets": [
#                                         {"key": "file1", 
#                                         "doc_count": 10}, 
#                                         {"key": "file2", 
#                                          "doc_count": 20}
#                                     ]},
#                                 "max_count": {
#                                     "value": 20, 
#                                     "keys": ["file2"]},
#                                 "ext_stats": {
#                                     "sum": 30, 
#                                     "avg": 15, 
#                                     "std_deviation": 5}
#                             }}
#     start = datetime(2023, 5, 1)
#     end = datetime(2023, 5, 5)
#     result = await log_database.log_overview(start, end)
#     self.assertIsInstance(result, LogOverview)
