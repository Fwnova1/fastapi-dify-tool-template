FROM python:3.11.4-slim-bullseye as prod
RUN apt-get update && apt-get install -y \
  gcc \
  && rm -rf /var/lib/apt/lists/*

RUN pip install poetry==1.8.2

# Configuring poetry
RUN poetry config virtualenvs.create false
RUN poetry config cache-dir /tmp/poetry_cache

# Copying requirements of a project
COPY pyproject.toml poetry.lock /app/src/
WORKDIR /app/src

# Installing requirements
RUN --mount=type=cache,target=/tmp/poetry_cache poetry install --only main

# Install additional dependencies
RUN pip install PyMuPDF

RUN apt-get update && apt-get install -y ffmpeg

# Removing gcc
RUN apt-get purge -y \
  gcc \
  && rm -rf /var/lib/apt/lists/*

# Copying actual application
COPY . /app/src/
RUN --mount=type=cache,target=/tmp/poetry_cache poetry install --only main

CMD ["/usr/local/bin/python", "-m", "app"]

FROM prod as dev

RUN --mount=type=cache,target=/tmp/poetry_cache poetry install
