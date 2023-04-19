# SmartLog Statistics Backend

Backend is based on the [Starlette Framework](https://www.starlette.io/) and on [Pydantic](https://docs.pydantic.dev/).

## Requisites

- Python 3.10 (3.11 should work but it's not tested)
- [Poetry](https://python-poetry.org/docs/#installation)

## Running

```sh
poetry install  # needed only on first run and on lockfile changes
poetry run gunicorn -k uvicorn.workers.UvicornWorker sl_statistics_backend:app  # production mode
poetry run python -m sl_statistics_backend  # dev mode, supports hot reload
```

Server binds by default at `127.0.0.1:8000`, so no access from other network devices and no IPv6.

## Documentation

API endpoints are documented using an OpenAPI (fka Swagger) specification available at `/apidoc/openapi.json` ([SwaggerUI](https://github.com/swagger-api/swagger-ui) available at `/apidoc/swagger`, [ReDoc](https://github.com/Redocly/redoc) available at `/apidoc/redoc`).
