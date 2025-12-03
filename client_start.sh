#!/bin/bash
# client_start.sh - Script to start Flotilla client
# Run this on CLIENT machines

set -e  # Exit on error

echo "=========================================="
echo "Flotilla Client Startup Script"
echo "=========================================="
echo ""

# Default values
SERVER_IP=""
CLIENT_NUM=1

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --server-ip)
            SERVER_IP="$2"
            shift 2
            ;;
        --client-num)
            CLIENT_NUM="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: ./client_start.sh --server-ip <SERVER_IP> [--client-num <NUM>]"
            echo ""
            echo "Arguments:"
            echo "  --server-ip    IP address of the Flotilla server (required)"
            echo "  --client-num   Client number (default: 1)"
            echo ""
            echo "Example:"
            echo "  ./client_start.sh --server-ip 192.168.1.100 --client-num 1"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if server IP is provided
if [ -z "$SERVER_IP" ]; then
    echo "❌ Error: Server IP is required"
    echo ""
    echo "Usage: ./client_start.sh --server-ip <SERVER_IP> [--client-num <NUM>]"
    echo ""
    echo "Example:"
    echo "  ./client_start.sh --server-ip 192.168.1.100 --client-num 1"
    exit 1
fi

# Get client IP
CLIENT_IP=$(hostname -I | awk '{print $1}')
echo "📍 Client IP Address: $CLIENT_IP"
echo "📍 Server IP Address: $SERVER_IP"
echo "📍 Client Number: $CLIENT_NUM"
echo ""

# Test connectivity to server
echo "Testing connection to server..."
if ping -c 1 -W 2 $SERVER_IP > /dev/null 2>&1; then
    echo "✓ Server is reachable"
else
    echo "❌ Cannot reach server at $SERVER_IP"
    echo "   Please check:"
    echo "   1. Server IP is correct"
    echo "   2. Both machines are on the same network"
    echo "   3. Firewall allows ICMP (ping)"
    exit 1
fi

# Test MQTT port
echo "Testing MQTT port 1884..."
if nc -zv -w 2 $SERVER_IP 1884 2>&1 | grep -q succeeded; then
    echo "✓ MQTT port 1884 is open"
else
    echo "⚠️  Warning: Cannot connect to MQTT port 1884"
    echo "   This might be a firewall issue"
    echo "   Continuing anyway..."
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    echo "✓ Virtual environment found"
fi

# Check if training data exists
if [ ! -d "src/data" ]; then
    echo "⚠️  Warning: src/data directory not found"
    echo "   You may need to create training datasets"
fi

echo ""
echo "=========================================="
echo "Starting Flotilla Client..."
echo "=========================================="
echo ""

# Activate virtual environment and start client
source .venv/bin/activate
python src/flo_client.py --server-ip $SERVER_IP --client-num $CLIENT_NUM
