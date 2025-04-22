FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install numpy onnxruntime scikit-learn colorama

CMD ["python", "app.py"]
