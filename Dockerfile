FROM python:3.11-slim

WORKDIR /app

COPY setup/models /app/models
COPY setup/artifact /app/artifact
COPY app.py /app

RUN pip install numpy onnxruntime scikit-learn colorama

CMD ["python", "app.py"]
