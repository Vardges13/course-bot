FROM python:3.12-slim

WORKDIR /app

# Зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Исходный код
COPY . .

# Директория для БД
RUN mkdir -p /app/data

CMD ["python", "-m", "bot"]
