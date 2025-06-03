FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    pkg-config \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p uploads results ai/models

RUN python -c "import flask; print('Flask OK')"
RUN python -c "import flask_cors; print('CORS OK')"
RUN python -c "import flask_jwt_extended; print('JWT OK')"
RUN python -c "import flask_mysqldb; print('MySQL OK')"

RUN python -c "from config import app, db; print('Config OK')"

EXPOSE 8080

CMD python -c "import os; os.environ.setdefault('PORT', '8080'); exec(open('app.py').read())"