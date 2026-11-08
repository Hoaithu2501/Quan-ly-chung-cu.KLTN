FROM node:22-alpine AS frontend-build
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY frontend ./frontend
RUN npm run build:css

FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app HOST=0.0.0.0
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY shared /app/shared
COPY gateway /app/gateway
COPY --from=frontend-build /build/frontend /app/frontend
EXPOSE 5000
CMD ["python", "gateway/app.py"]
