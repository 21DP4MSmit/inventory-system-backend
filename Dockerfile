FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install gunicorn==21.2.0
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads results ai/models

ENV PORT=8080
ENV PYTHONPATH=/app

EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app