from datetime import datetime
from functools import wraps
from typing import Any

from elasticsearch import AsyncElasticsearch
from elasticsearch._async.client.ingest import IngestClient
from elasticsearch.helpers import async_bulk
from sl_parser import LogFile
from typing_extensions import Self

from sl_statistics_backend.models import LogFrequencyEntry, LogOverview, MaxCountEntry, StoredLogFile, StoredLogList

_max_timestamp = datetime(2100, 12, 31, 23, 59, 59).timestamp() * 1000


class LogDatabaseError(Exception):
    message: str

    def __init__(self: Self, message: str, *args: object) -> None:
        super().__init__(*args)
        self.message = message


def _ensure_index_exists(f):  # noqa: ANN001, ANN202
    @wraps(f)
    async def wrapper(db: "LogDatabase", *args):  # noqa: ANN002, ANN202
        if not db._index_exists:
            if not await db.elastic.indices.exists(index=db.index_name):
                print("creating index")
                await db.elastic.indices.create(
                    index=db.index_name,
                    mappings={
                        "properties": {
                            "@timestamp": {"type": "date_nanos"},
                            "code": {"type": "keyword"},
                            "description": {"type": "text"},
                            "file": {"type": "keyword"},
                            "ini_filename": {"type": "keyword"},
                            "subunit": {"type": "long"},
                            "timestamp": {"type": "date_nanos", "format": "iso8601"},
                            "type_um": {"type": "keyword"},
                            "unit": {"type": "long"},
                            "unit_subunit_id": {"type": "long"},
                            "value": {"type": "keyword"},
                        }
                    },
                )
            await IngestClient(db.elastic).put_pipeline(
                id=db._pipeline_name,
                processors=[
                    {
                        "date": {
                            "field": "timestamp",
                            "timezone": "Europe/Rome",
                            "formats": ["ISO8601"],
                            "output_format": "yyyy-MM-dd'T'HH:mm:ss.SSSSSSSSSXXX",
                        }
                    },
                    {"remove": {"field": ["color", "snapshot"]}},
                ],
            )
            db._index_exists = True
        return await f(db, *args)

    return wrapper


class LogDatabase:
    elastic: AsyncElasticsearch
    index_name: str
    _pipeline_name: str
    _index_exists: bool

    def __init__(self: Self, elastic_url: str, index_name: str = "smartlog") -> None:
        self.elastic = AsyncElasticsearch(
            elastic_url,
            verify_certs=False,
        )
        self.index_name = index_name
        self._pipeline_name = index_name + "-pipeline"
        self._index_exists = False

    async def close(self: Self) -> None:
        await self.elastic.close()

    async def _composite_paginate(
        self: Self, index: str, agg: dict[str, dict[str, Any]], query: dict[str, dict[str, Any]] | None = None
    ) -> list[Any]:
        response = await self.elastic.search(
            index=index,
            size=0,
            query=query,
            aggs={"agg": agg},
        )
        data = response["aggregations"]["agg"]["buckets"]
        while "after_key" in response["aggregations"]["agg"]:
            agg["composite"]["after"] = response["aggregations"]["agg"]["after_key"]
            response = await self.elastic.search(
                index=index,
                size=0,
                query=query,
                aggs={"agg": agg},
            )
            data += response["aggregations"]["agg"]["buckets"]
        return data

    @property
    @_ensure_index_exists
    async def uploaded_file_list(self: Self) -> StoredLogList:
        log_files = await self._composite_paginate(
            self.index_name,
            {
                "composite": {"size": 1000, "sources": [{"filename": {"terms": {"field": "file"}}}]},
                "aggs": {
                    "min_timestamp": {"min": {"field": "@timestamp"}},
                    "max_timestamp": {"max": {"field": "@timestamp"}},
                },
            },
        )
        min_max = await self.elastic.search(
            index=self.index_name,
            size=0,
            aggs={"min_timestamp": {"min": {"field": "@timestamp"}}, "max_timestamp": {"max": {"field": "@timestamp"}}},
        )
        return StoredLogList(
            log_files=[
                StoredLogFile(
                    file_name=log_file["key"]["filename"],
                    first_entry_timestamp=datetime.fromtimestamp(log_file["min_timestamp"]["value"] / 1000),
                    last_entry_timestamp=datetime.fromtimestamp(log_file["max_timestamp"]["value"] / 1000),
                    entry_count=log_file["doc_count"],
                )
                for log_file in log_files
            ],
            min_timestamp=datetime.fromtimestamp(
                (min_max["aggregations"]["min_timestamp"]["value"] or 0) / 1000,
            ),
            max_timestamp=datetime.fromtimestamp(
                (min_max["aggregations"]["max_timestamp"]["value"] or _max_timestamp) / 1000,
            ),
        )

    @_ensure_index_exists
    async def _log_already_uploaded(self: Self, file_name: str) -> bool:
        res = await self.elastic.search(
            index=self.index_name,
            size=0,
            query={
                "term": {"file": {"value": file_name}},
            },
        )
        return res["hits"]["total"]["value"] != 0

    @_ensure_index_exists
    async def upload(self: Self, log_file: LogFile) -> int:
        if await self._log_already_uploaded(log_file.filename):
            raise LogDatabaseError("Log file already uploaded!")
        entries = ((e.dict() | {"file": log_file.filename}) for e in log_file.log_entries)
        count = (
            await async_bulk(
                self.elastic,
                actions=(
                    {
                        "_index": self.index_name,
                        "_source": entry,
                        "pipeline": self._pipeline_name,
                    }
                    for entry in entries
                ),
            )
        )[0]
        await self.elastic.indices.refresh(index=self.index_name)
        return count

    @_ensure_index_exists
    async def delete_log(self: Self, log: str) -> int:
        return (
            await self.elastic.delete_by_query(
                index=self.index_name, query={"bool": {"must": {"term": {"file": {"value": log}}}}}, refresh=True
            )
        )["total"]

    @_ensure_index_exists
    async def log_overview(self: Self, start: datetime, end: datetime) -> LogOverview:
        general_stats = await self.elastic.search(
            index=self.index_name,
            size=0,
            query={"bool": {"must": {"range": {"@timestamp": {"gte": start.isoformat(), "lte": end.isoformat()}}}}},
            aggregations={
                "file": {"terms": {"field": "file", "size": 100000000}},
                "max_count": {"max_bucket": {"buckets_path": "file>_count"}},
                "ext_stats": {"extended_stats_bucket": {"buckets_path": "file>_count"}},
            },
        )
        if general_stats["hits"]["total"]["value"] == 0:
            return LogOverview.empty()
        return LogOverview(
            total_entries=general_stats["aggregations"]["ext_stats"]["sum"],
            avg_entries=general_stats["aggregations"]["ext_stats"]["avg"],
            max_count_entry=MaxCountEntry(
                filename=general_stats["aggregations"]["max_count"]["keys"][0],
                entry_count=general_stats["aggregations"]["max_count"]["value"],
            ),
            entries_std_dev=general_stats["aggregations"]["ext_stats"]["std_deviation"],
        )

    @_ensure_index_exists
    async def log_entries_frequency(
        self: Self, start: datetime, end: datetime, subunits: list[int]
    ) -> list[LogFrequencyEntry]:
        frequency_stats = await self._composite_paginate(
            self.index_name,
            {
                "composite": {
                    "sources": [{"fw": {"terms": {"field": "ini_filename"}}}, {"code": {"terms": {"field": "code"}}}]
                }
            },
            {
                "bool": {
                    "must": [
                        {"term": {"type_um": {"value": "BIN"}}},
                        {"term": {"value": {"value": "ON"}}},
                        {"range": {"@timestamp": {"gte": start.isoformat(), "lte": end.isoformat()}}},
                        {"terms": {"unit_subunit_id": subunits}},
                    ]
                }
            },
        )
        return [
            LogFrequencyEntry(firmware=entry["key"]["fw"], event_code=entry["key"]["code"], count=entry["doc_count"])
            for entry in frequency_stats
        ]