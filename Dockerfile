FROM node:22-bookworm-slim AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM node:22-bookworm-slim AS pagekit
WORKDIR /src/pagekit
COPY pagekit/package.json pagekit/package-lock.json ./
RUN npm ci

FROM python:3.12-slim-bookworm
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && node --version

COPY pyproject.toml ./
COPY studio ./studio
RUN pip install --no-cache-dir .

COPY --from=web /src/web/dist ./web/dist
COPY pagekit ./pagekit
COPY --from=pagekit /src/pagekit/node_modules ./pagekit/node_modules

ENV STUDIO_HOST=0.0.0.0
ENV STUDIO_PORT=8080
ENV PUBLISH_MODE=static
ENV DATA_DIR=/app/persist/data
ENV SITES_DIR=/app/persist/sites
EXPOSE 8080
CMD ["python", "-m", "studio"]
