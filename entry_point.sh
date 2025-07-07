#!/usr/bin/env bash
set -e

# Create log directory for nginx
mkdir -p /var/log/nginx

# 1️⃣ background MLflow Tracking UI
echo "Starting MLflow UI..."
mlflow ui --host 0.0.0.0 --port 5000 &             # serves at :5000

# 2️⃣ background Streamlit
echo "Starting Streamlit..."
streamlit run /app/streamlit_ui.py \
  --server.port 8501 \
  --server.address 0.0.0.0 &                       # serves at :8501

# Give services time to start
sleep 5

# Test if services are responding
echo "Testing services..."
curl -f http://localhost:5000 > /dev/null && echo "MLflow OK" || echo "MLflow FAILED"
curl -f http://localhost:8501 > /dev/null && echo "Streamlit OK" || echo "Streamlit FAILED"

# 3️⃣ foreground NGINX (keeps the container alive)
echo "Starting nginx..."
nginx -g 'daemon off;'
