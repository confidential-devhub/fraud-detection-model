# Stage 1: build — install deps and run create_model to produce model + artifact
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY data /app/data
COPY create_model.py /app
RUN python create_model.py

# Stage 2: final image — only the built model and the app
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends openssl && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir numpy onnxruntime colorama scikit-learn azure.storage.blob
COPY --from=builder /app/models /app/models
COPY --from=builder /app/artifact /app/artifact
RUN mkdir -p /app/downloaded_datasets /app/default_datasets && chmod 1777 /app/downloaded_datasets
COPY default.csv /app/default_datasets/default.csv
COPY app.py /app
ENV PYTHONUNBUFFERED=1
CMD ["python", "-u", "app.py"]
