from starlette.config import Config
from starlette.datastructures import URL

config = Config(".env")

DEBUG = config("DEBUG", cast=bool, default=False)
DISABLE_CORS = config("DISABLE_CORS", cast=bool, default=False)
ELASTICSEARCH_URL = config("ELASTICSEARCH_URL", cast=URL)
