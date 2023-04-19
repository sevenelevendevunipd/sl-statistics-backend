# Build venv in a separate stage in order to minimize final image size
FROM python:3.10-alpine AS builder
ARG WORKDIR

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
RUN apk add gcc musl-dev libffi-dev && pip install poetry && poetry config virtualenvs.in-project true
WORKDIR /app
COPY poetry.lock pyproject.toml ./
RUN poetry install -n --no-root --without=dev



FROM python:3.10-alpine

ARG WORKDIR
WORKDIR /app
COPY --from=builder /app .
COPY entrypoint.sh .
COPY sl_statistics_backend sl_statistics_backend

ENTRYPOINT [ "/app/entrypoint.sh" ]
