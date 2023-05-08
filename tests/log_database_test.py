# ruff: noqa: PLR2004

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from elasticsearch import AsyncElasticsearch
from elasticsearch._async.client.ingest import IngestClient
from sl_parser import LogEntry, LogFile, Unit

from sl_statistics_backend.log_database import LogDatabase, LogDatabaseError
from sl_statistics_backend.models import (
    LogFrequencyEntry,
    LogOverview,
    StoredLogList,
)

mock_elastic = AsyncMock()


@pytest.fixture(scope="function")
def log_database() -> LogDatabase:
    index_name = "test_smartlog"
    log_db = LogDatabase(mock_elastic, index_name)
    return log_db


@pytest.fixture(scope="session")
def log_file() -> LogFile:
    entries = [
        LogEntry(
            timestamp=datetime.now(),
            code="AplCmdErrorUnitSubunit",
            description="AplCmdErrorUnitSubunit",
            ini_filename="MAPK_Unit_v2_02_00.ini",
            subunit=0,
            type_um="HEX",
            unit=1,
            unit_subunit_id=0,
            value="0x0000",
            snapshot="0",
            color="0xFFADFF2F",
        )
    ]
    pc_datetime = datetime.now()
    ups_datetime = datetime.now()
    units_subunits = {1: Unit(ini_file="firmware1", subunits={1: "subunit1", 2: "subunit2"})}

    log_file = LogFile(
        filename="test.log",
        pc_datetime=pc_datetime,
        ups_datetime=ups_datetime,
        units_subunits=units_subunits,
        log_entries=entries,
    )

    return log_file


@pytest.mark.asyncio
async def test_upload(log_database: LogDatabase, log_file: LogFile) -> None:
    # Test uploading a log file
    with patch.object(log_database, "_log_already_uploaded", return_value=False), patch.object(
        log_database, "_call_async_bulk", return_value=(1, 0)
    ):
        result = await log_database.upload(log_file)
        assert result == 1

    # Test that an exception is raised if the log file was already uploaded
    with pytest.raises(LogDatabaseError):
        await log_database.upload(log_file)


@pytest.mark.asyncio
async def test_uploaded_file_list(log_database: LogDatabase) -> None:
    # quando viene fatto il mock di elasticsearch viene restituita log_files vuota e il primo datetime possibile,
    # a meno che non gli venga esplicitamente detto di restituire qualcos'altro ma nel nostro caso non serve.
    expected_result = StoredLogList(
        log_files=[],
        min_timestamp=datetime(1970, 1, 1, 1, 0, 1),
        max_timestamp=datetime(1970, 1, 1, 1, 0, 1),
    )

    # Test getting the list of uploaded log files
    result = await log_database.uploaded_file_list
    assert result == expected_result


@pytest.mark.asyncio
async def test_composite_paginate(log_database: LogDatabase) -> None:
    mock_elastic.search = AsyncMock(
        side_effect=[
            {
                "aggregations": {
                    "agg": {
                        "buckets": [
                            {"key": "value1", "doc_count": 10},
                            {"key": "value2", "doc_count": 5},
                            {"key": "value3", "doc_count": 2},
                        ],
                        "after_key": "value3",
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
            },
        ]
    )
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


@pytest.mark.asyncio
async def test_log_overview(log_database: LogDatabase) -> None:
    mock_elastic.search.side_effect = [
        {
            "hits": {"total": {"value": 1}},
            "aggregations": {
                "file": {"buckets": [{"key": "file1", "doc_count": 100}, {"key": "file2", "doc_count": 50}]},
                "max_count": {"value": 100, "keys": ["file1"]},
                "ext_stats": {"count": 2, "sum": 150, "avg": 75, "std_deviation": 25},
            },
        }
    ]

    start = datetime(2023, 4, 1)
    end = datetime(2023, 4, 30)

    result = await log_database.log_overview(start, end)
    assert result.total_entries == 150
    assert result.avg_entries == 75
    assert result.max_count_entry.filename == "file1"
    assert result.max_count_entry.entry_count == 100
    assert result.entries_std_dev == 25

    mock_elastic.search.side_effect = [
        {
            "hits": {"total": {"value": 0}},
        }
    ]

    result = await log_database.log_overview(start, end)
    assert result == LogOverview.empty()


@pytest.mark.asyncio
async def test_log_entries_frequency(log_database: LogDatabase) -> None:
    expected_result = [
        LogFrequencyEntry(firmware="firmware1", event_code="event1", count=10),
        LogFrequencyEntry(firmware="firmware2", event_code="event2", count=20),
        LogFrequencyEntry(firmware="firmware3", event_code="event3", count=30),
    ]
    mock_response = [
        {"key": {"fw": "firmware1", "code": "event1"}, "doc_count": 10},
        {"key": {"fw": "firmware2", "code": "event2"}, "doc_count": 20},
        {"key": {"fw": "firmware3", "code": "event3"}, "doc_count": 30},
    ]
    with patch.object(log_database, "_composite_paginate", return_value=mock_response):
        start = datetime(2023, 5, 1)
        end = datetime(2023, 5, 5)
        subunits = [1, 2, 3]
        result = await log_database.log_entries_frequency(start, end, subunits)
        assert result == expected_result


@pytest.mark.asyncio
async def test_chart_filters(log_database: LogDatabase) -> None:
    start = datetime(2023, 5, 1)
    end = datetime(2023, 5, 2)
    expected_codes = ["code1", "code2", "code3"]
    expected_firmwares = ["firmware1", "firmware2", "firmware3"]
    expected_subunits = [2, 1, 2]

    mock_paginate = AsyncMock(
        side_effect=[
            [{"key": {"code": code}} for code in expected_codes],
            [{"key": {"firmware": firmware}} for firmware in expected_firmwares],
            [{"key": {"subunit": subunit}} for subunit in expected_subunits],
        ]
    )

    with patch.object(log_database, "_composite_paginate", new=mock_paginate):
        result = await log_database.chart_filters(start, end)

    assert result.codes == expected_codes
    assert result.firmwares == expected_firmwares
    assert result.subunits == expected_subunits


@pytest.mark.asyncio
async def test_time_chart_data(log_database: LogDatabase) -> None:
    expected_result = [{"timestamp": "2023-05-05T00:00:00.000Z", "total": 10, "CODE1": 5, "CODE2": "0"}]

    mock_elastic.search.side_effect = [
        {
            "hits": {"total": {"value": 1}},
            "aggregations": {
                "events_over_time": {
                    "buckets": [
                        {
                            "key_as_string": "2023-05-05T00:00:00.000Z",
                            "doc_count": 10,
                            "filtered": {"code": {"buckets": [{"key": "CODE1", "doc_count": 5}]}},
                        }
                    ]
                }
            },
        }
    ]

    start = datetime(2023, 5, 1)
    end = datetime(2023, 5, 7)
    subunits = [1, 2, 3]
    codes = ["CODE1", "CODE2"]

    result = await log_database.time_chart_data(start, end, subunits, codes)
    assert result == expected_result

    mock_elastic.search.side_effect = [
        {
            "hits": {"total": {"value": 0}},
        }
    ]

    result = await log_database.time_chart_data(start, end, subunits, codes)
    assert result == []


@pytest.mark.asyncio
async def test_firmware_chart_data(log_database: LogDatabase) -> None:
    expected_result = [
        {"firmware": "firmware1", "total": 100, "code1": 10, "code2": 20, "code3": 30},
        {"firmware": "firmware2", "total": 50, "code1": 5, "code2": 15, "code3": 25},
    ]

    mock_response = [
        {
            "key": {"firmware": "firmware1"},
            "doc_count": 100,
            "filtered": {
                "code": {
                    "buckets": [
                        {"key": "code1", "doc_count": 10},
                        {"key": "code2", "doc_count": 20},
                        {"key": "code3", "doc_count": 30},
                    ]
                }
            },
        },
        {
            "key": {"firmware": "firmware2"},
            "doc_count": 50,
            "filtered": {
                "code": {
                    "buckets": [
                        {"key": "code1", "doc_count": 5},
                        {"key": "code2", "doc_count": 15},
                        {"key": "code3", "doc_count": 25},
                    ]
                }
            },
        },
    ]

    start = datetime(2022, 1, 1)
    end = datetime(2022, 1, 31)
    firmwares = ["firmware1", "firmware2"]
    codes = ["code1", "code2", "code3"]

    with patch.object(log_database, "_composite_paginate", return_value=mock_response):
        result = await log_database.firmware_chart_data(start, end, firmwares, codes)

    assert result == expected_result


@pytest.mark.asyncio
async def test_ensure_index_exists_creates_index() -> None:
    es = AsyncElasticsearch(hosts=["http://fakeurl:9200/"])
    log_database = LogDatabase(es)
    with patch.object(es.indices, "exists", new_callable=AsyncMock) as mock_exists, patch.object(
        es.indices, "create", new_callable=AsyncMock
    ) as mock_create, patch.object(IngestClient, "put_pipeline", new_callable=AsyncMock) as mock_put_pipeline:
        mock_exists.return_value = False
        await log_database.ensure_index_exists()
        mock_exists.assert_called_once_with(index=log_database.index_name)
        mock_create.assert_called_once()
        mock_put_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_ensure_index_exists_doesnt_create_index() -> None:
    es = AsyncElasticsearch(hosts=["http://fakeurl:9200/"])
    log_database = LogDatabase(es)
    with patch.object(es.indices, "exists", new_callable=AsyncMock) as mock_exists, patch.object(
        es.indices, "create"
    ) as mock_create:
        mock_exists.return_value = True
        await log_database.ensure_index_exists()
        mock_exists.assert_called_once_with(index=log_database.index_name)
        mock_create.assert_not_called()
