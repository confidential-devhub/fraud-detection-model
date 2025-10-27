#!/bin/bash

rm -rf models
rm -rf artifact

pip install -r requirements.txt
python create_model.py

podman build -t fraud-detection .