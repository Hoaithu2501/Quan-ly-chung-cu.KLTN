# One recipe for every image. docker-compose.yml picks the stage, and which service to build.

FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app HOST=0.0.0.0
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY shared shared
RUN useradd --system --uid 10001 --no-create-home app


# Creates and migrates the database, and takes the daily backups.
# Runs as root so it can hand the data volume over to the unprivileged app user.
FROM base AS init
COPY scripts scripts
COPY migrations migrations
COPY tests/fixtures/demo.sql tests/fixtures/demo.sql


# One business service, chosen with the SERVICE build argument.
FROM base AS service
ARG SERVICE
ENV SERVICE_APP=${SERVICE}-service/app.py
COPY ${SERVICE}-service ${SERVICE}-service
COPY scripts/check_firebase.py scripts/check_firebase.py
USER 10001
CMD ["sh", "-c", "exec python \"$SERVICE_APP\""]


# Compiles the Tailwind stylesheet for the gateway image.
FROM node:22-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY frontend frontend
RUN npm run build:css


# The website and the API reverse proxy.
FROM base AS gateway
COPY gateway gateway
COPY --from=frontend /build/frontend frontend
USER 10001
EXPOSE 5000
CMD ["python", "gateway/app.py"]
