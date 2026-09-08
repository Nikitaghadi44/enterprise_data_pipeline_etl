FROM python:3.11-slim

WORKDIR /app

# System deps for mysqlclient/pymysql + healthcheck curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-libmysqlclient-dev build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs /app/exports /app/data

EXPOSE 5000

# Default: run the dashboard. Overridden per-service in docker-compose.yml.
CMD ["python", "main.py", "dashboard"]
