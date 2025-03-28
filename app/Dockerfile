FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    iputils-ping \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/app.py .
COPY app/templates ./templates
COPY app/static ./static

RUN mkdir -p /certs
COPY nginx/certs/server.crt /certs/server.crt
COPY nginx/certs/server.key /certs/server.key

EXPOSE 5000

CMD ["python", "app.py"]