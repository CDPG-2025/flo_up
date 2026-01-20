#!/bin/bash
set -e

source venv/bin/activate

cd docker
docker-compose up -d
cd ..

cd src
pkill -f python || true

python flo_server.py
