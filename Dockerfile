FROM node:24-alpine AS workspace
WORKDIR /workspace
COPY web/package*.json ./
RUN npm ci
COPY web ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY grd ./grd
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home grd
COPY alembic.ini ./
COPY migrations ./migrations
COPY --from=workspace /workspace/dist ./web/dist
ENV GRD_WEB_DIST=/app/web/dist
USER grd
EXPOSE 8000
CMD ["uvicorn", "grd.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
