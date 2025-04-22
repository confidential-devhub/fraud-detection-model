#!/bin/bash

cd setup
pip install -r requirements.txt
python create_model.py
cd -

podman build -t fraud-detection .