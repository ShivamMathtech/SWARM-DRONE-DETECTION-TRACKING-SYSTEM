FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir torch==2.7.1 torchvision==0.22.1 --index-url https://download.pytorch.org/whl/cpu && pip install --no-cache-dir -r backend/requirements.txt
COPY backend /app/backend
COPY weights /app/weights
RUN useradd -m -u 10001 swarm && mkdir -p /app/data && chown -R swarm:swarm /app
USER swarm
WORKDIR /app/backend
EXPOSE 8000
CMD ["python","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
