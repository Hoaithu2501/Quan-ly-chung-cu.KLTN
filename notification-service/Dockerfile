FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app HOST=0.0.0.0
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY shared /app/shared
COPY notification-service /app/notification-service
COPY scripts/check_firebase.py /app/scripts/check_firebase.py
EXPOSE 5006
CMD ["python", "notification-service/app.py"]
