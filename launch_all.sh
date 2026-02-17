#!/bin/bash
# Launch ChatterFix Intelligence Platform
# Admin Dashboard: http://localhost:8501
# Client Portal:   http://localhost:8502

echo "======================================"
echo "ChatterFix Intelligence Platform"
echo "======================================"
echo ""

# Check for required packages
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo "Installing required packages..."
    pip install -r dashboard/requirements.txt
fi

# Kill any existing instances
pkill -f "streamlit run dashboard" 2>/dev/null

echo "Starting services..."
echo ""

# Launch Admin Dashboard (port 8501)
streamlit run dashboard/app.py --server.port 8501 --server.headless true &
ADMIN_PID=$!

# Wait a moment
sleep 2

# Launch Client Portal (port 8502)
streamlit run dashboard/client_portal.py --server.port 8502 --server.headless true &
CLIENT_PID=$!

echo ""
echo "======================================"
echo "Services Running:"
echo "======================================"
echo ""
echo "  ADMIN DASHBOARD:  http://localhost:8501"
echo "  CLIENT PORTAL:    http://localhost:8502"
echo ""
echo "  Client Portal Demo Login:"
echo "    Username: queso"
echo "    Password: cheese2024"
echo ""
echo "======================================"
echo "Press Ctrl+C to stop all services"
echo "======================================"

# Wait for either process to exit
wait $ADMIN_PID $CLIENT_PID
