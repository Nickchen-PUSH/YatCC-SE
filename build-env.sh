#!/bin/bash

apt update
apt install -y python3 python3-pip python3-venv redis podman buildah skopeo wget

python3 -m venv venv
. venv/bin/activate
pip install 'flask[async]' gunicorn redis cryptography httpx locust \
    'flask-openapi3[swagger, redoc, rapidoc, rapipdf, scalar, elements]' \
    coverage kubernetes
