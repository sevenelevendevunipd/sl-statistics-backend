from starlette.routing import Mount

from .charts import ChartMount
from .log_aggregation import LogAggregationMount
from .log_management import LogManagementMount

ApiMount = Mount(
    "/api",
    routes=[
        ChartMount,
        LogAggregationMount,
        LogManagementMount,
    ],
)
