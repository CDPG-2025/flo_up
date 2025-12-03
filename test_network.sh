#!/bin/bash
# test_network.sh - Test network connectivity for Flotilla
# Run this script to verify network setup before starting Flotilla

echo "=========================================="
echo "Flotilla Network Connectivity Test"
echo "=========================================="
echo ""

# Determine if this is server or client
echo "Are you running this on the SERVER or CLIENT machine?"
echo "1) Server"
echo "2) Client"
read -p "Enter choice (1 or 2): " MACHINE_TYPE

if [ "$MACHINE_TYPE" == "1" ]; then
    echo ""
    echo "=== SERVER MACHINE TESTS ==="
    echo ""
    
    # Get server IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo "📍 Server IP: $SERVER_IP"
    echo "   (Clients will use: --server-ip $SERVER_IP)"
    echo ""
    
    # Check Docker
    echo "Checking Docker..."
    if docker info > /dev/null 2>&1; then
        echo "✓ Docker is running"
    else
        echo "❌ Docker is not running"
        exit 1
    fi
    
    # Check Docker services
    echo ""
    echo "Checking Docker services..."
    if docker ps | grep -q mqtt_broker; then
        echo "✓ MQTT Broker is running"
    else
        echo "❌ MQTT Broker is not running"
        echo "   Run: cd docker && docker-compose up -d"
    fi
    
    if docker ps | grep -q redis_server; then
        echo "✓ Redis Server is running"
    else
        echo "❌ Redis Server is not running"
        echo "   Run: cd docker && docker-compose up -d"
    fi
    
    # Check ports
    echo ""
    echo "Checking ports..."
    
    if netstat -tuln | grep -q ":1884"; then
        echo "✓ Port 1884 (MQTT) is listening"
    else
        echo "❌ Port 1884 (MQTT) is not listening"
    fi
    
    if netstat -tuln | grep -q ":6379"; then
        echo "✓ Port 6379 (Redis) is listening"
    else
        echo "❌ Port 6379 (Redis) is not listening"
    fi
    
    # Check firewall
    echo ""
    echo "Checking firewall rules..."
    if command -v ufw &> /dev/null; then
        if sudo ufw status | grep -q "1884.*ALLOW"; then
            echo "✓ Firewall allows port 1884"
        else
            echo "⚠️  Firewall may not allow port 1884"
            echo "   Run: sudo ufw allow 1884/tcp"
        fi
        
        if sudo ufw status | grep -q "12345.*ALLOW"; then
            echo "✓ Firewall allows port 12345"
        else
            echo "⚠️  Firewall may not allow port 12345"
            echo "   Run: sudo ufw allow 12345/tcp"
        fi
    else
        echo "⚠️  UFW not installed, cannot check firewall"
    fi
    
    echo ""
    echo "=== SERVER SETUP COMPLETE ==="
    echo "Next: Start clients with: --server-ip $SERVER_IP"
    
elif [ "$MACHINE_TYPE" == "2" ]; then
    echo ""
    echo "=== CLIENT MACHINE TESTS ==="
    echo ""
    
    # Get client IP
    CLIENT_IP=$(hostname -I | awk '{print $1}')
    echo "📍 Client IP: $CLIENT_IP"
    echo ""
    
    # Ask for server IP
    read -p "Enter SERVER IP address: " SERVER_IP
    
    # Test connectivity
    echo ""
    echo "Testing connectivity to server ($SERVER_IP)..."
    
    if ping -c 3 -W 2 $SERVER_IP > /dev/null 2>&1; then
        echo "✓ Server is reachable (ping successful)"
    else
        echo "❌ Cannot ping server"
        echo "   Check network connection"
        exit 1
    fi
    
    # Test MQTT port
    echo ""
    echo "Testing MQTT port (1884)..."
    if command -v nc &> /dev/null; then
        if nc -zv -w 2 $SERVER_IP 1884 2>&1 | grep -q succeeded; then
            echo "✓ MQTT port 1884 is accessible"
        else
            echo "❌ Cannot connect to MQTT port 1884"
            echo "   Check server firewall"
        fi
    else
        echo "⚠️  netcat (nc) not installed, cannot test ports"
        echo "   Install with: sudo apt-get install netcat"
    fi
    
    # Test REST API port
    echo ""
    echo "Testing REST API port (12345)..."
    if command -v nc &> /dev/null; then
        if nc -zv -w 2 $SERVER_IP 12345 2>&1 | grep -q succeeded; then
            echo "✓ REST API port 12345 is accessible"
        else
            echo "⚠️  Cannot connect to REST API port 12345"
            echo "   (This is OK if server is not running yet)"
        fi
    fi
    
    # Check local gRPC ports
    echo ""
    echo "Checking local gRPC ports..."
    if netstat -tuln | grep -q ":50053"; then
        echo "⚠️  Port 50053 is already in use"
        echo "   Use --client-num 2 or higher"
    else
        echo "✓ Port 50053 is available"
    fi
    
    # Check firewall
    echo ""
    echo "Checking firewall rules..."
    if command -v ufw &> /dev/null; then
        if sudo ufw status | grep -q "50053.*ALLOW"; then
            echo "✓ Firewall allows port 50053"
        else
            echo "⚠️  Firewall may not allow port 50053"
            echo "   Run: sudo ufw allow 50053/tcp"
        fi
    else
        echo "⚠️  UFW not installed, cannot check firewall"
    fi
    
    # Check data directory
    echo ""
    echo "Checking data directory..."
    if [ -d "src/data" ]; then
        echo "✓ src/data directory exists"
        DATASETS=$(find src/data -mindepth 1 -maxdepth 1 -type d | wc -l)
        echo "  Found $DATASETS dataset(s)"
    else
        echo "❌ src/data directory not found"
        echo "   Create training datasets first"
    fi
    
    echo ""
    echo "=== CLIENT SETUP COMPLETE ==="
    echo "Next: Run client with:"
    echo "  ./client_start.sh --server-ip $SERVER_IP --client-num 1"
    
else
    echo "Invalid choice"
    exit 1
fi

echo ""
echo "=========================================="
echo "Network test complete!"
echo "=========================================="
