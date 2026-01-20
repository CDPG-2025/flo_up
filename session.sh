#!/bin/bash
set -e

source venv/bin/activate

cd docker
docker-compose up -d
cd ..

pkill -f python || true

cd src && python flo_session.py ../config/flotilla_quicksetup_config.yaml \
  --federated_server_endpoint localhost:12345
