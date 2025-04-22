#!/bin/bash

cd setup
python -r requirements.txt
python create_model.py
cd -

podman build -t fraud-detection .