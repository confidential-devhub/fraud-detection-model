FROM python:3.11-slim

RUN cd setup
RUN python -r requirements.txt
RUN python create_model.py
RUN cd -

WORKDIR /app

COPY . /app

RUN pip install numpy onnxruntime scikit-learn colorama

CMD ["python", "app.py"]
