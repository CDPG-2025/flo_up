#!/bin/bash
# server_start.sh - Script to start Flotilla server components
# Run this on the SERVER machine

set -e  # Exit on error

echo "=========================================="
echo "Flotilla Server Startup Script"
echo "=========================================="
echo ""

# Get server IP
SERVER_IP=$(hostname -I | awk '{print $1}')
echo "📍 Server IP Address: $SERVER_IP"
echo "   (Clients will use this IP with --server-ip argument)"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi
echo "✓ Docker is running"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    echo "✓ Virtual environment found"
fi

# Start Docker services
echo ""
echo "Starting Docker services (MQTT & Redis)..."
cd docker
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 5

# Check if services are running
if docker ps | grep -q mqtt_broker; then
    echo "✓ MQTT Broker is running (port 1884)"
else
    echo "❌ MQTT Broker failed to start"
    exit 1
fi

if docker ps | grep -q redis_server; then
    echo "✓ Redis Server is running (port 6379)"
else
    echo "❌ Redis Server failed to start"
    exit 1
fi

cd ..

# Check if validation data exists
if [ ! -d "val_data" ]; then
    echo "⚠️  Warning: val_data directory not found"
    echo "   You may need to create validation datasets"
fi

echo ""
echo "=========================================="
echo "Docker services started successfully!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. In this terminal, run:"
echo "   source .venv/bin/activate"
echo "   python src/flo_server.py"
echo ""
echo "2. In another terminal, run:"
echo "   source .venv/bin/activate"
echo "   python src/flo_session.py"
echo ""
echo "3. On client machines, run:"
echo "   python src/flo_client.py --server-ip $SERVER_IP --client-num 1"
echo ""
echo "=========================================="
