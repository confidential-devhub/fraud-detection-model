#!/bin/bash

rm -rf setup/models
rm -rf setup/artifact

cd setup
pip install -r requirements.txt
python create_model.py
cd -

podman build -t fraud-detection .