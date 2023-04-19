import os

import uvicorn
from uvicorn.config import LOGGING_CONFIG

os.environ["STARLETTE_DEBUG"] = "true"

LOGGING_CONFIG["formatters"]["default"]["fmt"] = "%(asctime)s " + LOGGING_CONFIG["formatters"]["default"]["fmt"]
LOGGING_CONFIG["formatters"]["access"]["fmt"] = "%(asctime)s " + LOGGING_CONFIG["formatters"]["access"]["fmt"]

uvicorn.run("sl_statistics_backend:app", log_level="info", reload=True, log_config=LOGGING_CONFIG)
