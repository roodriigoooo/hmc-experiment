FROM node:22-slim AS build
WORKDIR /app
COPY package*.json tsconfig.json index.html ./
COPY web ./web
COPY scripts/build.mjs ./scripts/build.mjs
RUN npm ci && npm run build
FROM python:3.12-slim
WORKDIR /app
RUN useradd --uid 10001 --create-home study && mkdir /data && chown study /data
COPY --from=build /app/dist ./dist
COPY server ./server
COPY docs ./docs
COPY scripts/backup.py scripts/build-id.py ./scripts/
USER study
ENV HOST=0.0.0.0 DATABASE_PATH=/data/study.sqlite
EXPOSE 8000
CMD ["python", "-m", "server.app"]
