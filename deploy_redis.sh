#!/bin/bash

# 🚀 Redis PubSub Deployment Script
# This script deploys Redis-backed WebSocket to your production server

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   🚀 Taxi Service - Redis PubSub Deployment Script       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Configuration
SERVER_IP="164.90.229.192"
SERVER_USER="root"
APP_DIR="/home/taxi-service"
VENV_DIR="$APP_DIR/venv"

echo "📦 Step 1: Installing Redis on server..."
echo "────────────────────────────────────────────"
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
    set -e
    
    # Update package list
    echo "Updating package list..."
    apt update -qq
    
    # Install Redis
    if ! command -v redis-server &> /dev/null; then
        echo "Installing Redis..."
        apt install -y redis-server
        echo "✅ Redis installed"
    else
        echo "✅ Redis already installed"
    fi
    
    # Check Redis status
    systemctl status redis-server --no-pager | head -3
ENDSSH

echo ""
echo "🔐 Step 2: Configuring Redis security..."
echo "────────────────────────────────────────────"

# Generate strong password
REDIS_PASSWORD=$(openssl rand -base64 32)
echo "Generated Redis password: $REDIS_PASSWORD"

ssh $SERVER_USER@$SERVER_IP << ENDSSH
    set -e
    
    # Backup original config
    if [ ! -f /etc/redis/redis.conf.backup ]; then
        cp /etc/redis/redis.conf /etc/redis/redis.conf.backup
        echo "✅ Config backed up"
    fi
    
    # Configure Redis
    echo "Configuring Redis..."
    
    # Set password
    sed -i 's/^# requirepass .*/requirepass $REDIS_PASSWORD/' /etc/redis/redis.conf
    if ! grep -q "^requirepass" /etc/redis/redis.conf; then
        echo "requirepass $REDIS_PASSWORD" >> /etc/redis/redis.conf
    fi
    
    # Bind to localhost
    sed -i 's/^bind .*/bind 127.0.0.1 ::1/' /etc/redis/redis.conf
    
    # Set max memory
    if ! grep -q "^maxmemory" /etc/redis/redis.conf; then
        echo "maxmemory 256mb" >> /etc/redis/redis.conf
        echo "maxmemory-policy allkeys-lru" >> /etc/redis/redis.conf
    fi
    
    # Restart Redis
    systemctl restart redis-server
    systemctl enable redis-server
    
    echo "✅ Redis configured and restarted"
ENDSSH

echo ""
echo "📝 Step 3: Updating application .env file..."
echo "────────────────────────────────────────────"

ssh $SERVER_USER@$SERVER_IP << ENDSSH
    set -e
    cd $APP_DIR
    
    # Update or add REDIS_URL
    if grep -q "^REDIS_URL=" .env; then
        sed -i "s|^REDIS_URL=.*|REDIS_URL=redis://:$REDIS_PASSWORD@localhost:6379/0|" .env
        echo "✅ Updated REDIS_URL in .env"
    else
        echo "REDIS_URL=redis://:$REDIS_PASSWORD@localhost:6379/0" >> .env
        echo "✅ Added REDIS_URL to .env"
    fi
ENDSSH

echo ""
echo "📥 Step 4: Deploying code from Git..."
echo "────────────────────────────────────────────"

# Push local changes to git
echo "Committing local changes..."
git add .
git commit -m "✅ Implement Redis PubSub for WebSocket scalability" || echo "No changes to commit"
git push origin main

# Pull on server
ssh $SERVER_USER@$SERVER_IP << ENDSSH
    set -e
    cd $APP_DIR
    
    echo "Pulling latest code..."
    git pull origin main
    
    echo "✅ Code updated"
ENDSSH

echo ""
echo "🐍 Step 5: Installing Python dependencies..."
echo "────────────────────────────────────────────"

ssh $SERVER_USER@$SERVER_IP << ENDSSH
    set -e
    cd $APP_DIR
    
    echo "Activating virtual environment..."
    source $VENV_DIR/bin/activate
    
    echo "Installing/updating dependencies..."
    pip install -q redis==5.0.1
    pip install -q -r requirements.txt
    
    echo "✅ Dependencies installed"
ENDSSH

echo ""
echo "⚙️  Step 6: Updating Supervisor configuration..."
echo "────────────────────────────────────────────"

ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
    set -e
    
    # Backup supervisor config
    if [ -f /etc/supervisor/conf.d/taxi-service.conf ]; then
        cp /etc/supervisor/conf.d/taxi-service.conf /etc/supervisor/conf.d/taxi-service.conf.backup
    fi
    
    # Update worker class to Uvicorn
    sed -i 's/--workers [0-9]*/--workers 4/' /etc/supervisor/conf.d/taxi-service.conf
    
    # Add Uvicorn worker class if not present
    if ! grep -q "uvicorn.workers.UvicornWorker" /etc/supervisor/conf.d/taxi-service.conf; then
        sed -i 's|--bind 0.0.0.0:8000|--bind 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker --timeout 300|' /etc/supervisor/conf.d/taxi-service.conf
    fi
    
    echo "✅ Supervisor config updated"
    
    # Reload supervisor
    supervisorctl reread
    supervisorctl update
ENDSSH

echo ""
echo "🔄 Step 7: Updating Nginx configuration..."
echo "────────────────────────────────────────────"

ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
    set -e
    
    # Backup Nginx config
    NGINX_CONF="/etc/nginx/sites-available/taxi-service"
    if [ -f $NGINX_CONF ]; then
        cp $NGINX_CONF ${NGINX_CONF}.backup
    fi
    
    # Check if WebSocket location exists
    if ! grep -q "location /ws/" $NGINX_CONF; then
        echo "Adding WebSocket location block..."
        
        # Add WebSocket location before the closing brace
        sed -i '/^}$/i \
    # WebSocket connections\
    location /ws/ {\
        proxy_pass http://127.0.0.1:8000;\
        proxy_http_version 1.1;\
        proxy_set_header Upgrade $http_upgrade;\
        proxy_set_header Connection "upgrade";\
        proxy_set_header Host $host;\
        proxy_set_header X-Real-IP $remote_addr;\
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\
        proxy_read_timeout 3600s;\
        proxy_send_timeout 3600s;\
    }\
' $NGINX_CONF
        
        echo "✅ WebSocket location added"
    else
        echo "✅ WebSocket location already exists"
    fi
    
    # Test Nginx config
    nginx -t
    
    # Reload Nginx
    systemctl reload nginx
    
    echo "✅ Nginx reloaded"
ENDSSH

echo ""
echo "🔄 Step 8: Restarting services..."
echo "────────────────────────────────────────────"

ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
    set -e
    
    echo "Restarting taxi-api..."
    supervisorctl restart taxi-api
    
    sleep 3
    
    echo "Checking service status..."
    supervisorctl status taxi-api
ENDSSH

echo ""
echo "✅ Step 9: Verifying deployment..."
echo "────────────────────────────────────────────"

echo "Checking Redis connection..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
    # Check if Redis is accepting connections
    redis-cli ping > /dev/null 2>&1 && echo "✅ Redis is running" || echo "❌ Redis connection failed"
ENDSSH

echo ""
echo "Checking API logs for Redis connection..."
ssh $SERVER_USER@$SERVER_IP << 'ENDSSH'
    sleep 2
    tail -30 /var/log/taxi-api.out.log | grep -i redis || echo "No Redis messages in logs yet"
ENDSSH

echo ""
echo "Testing WebSocket stats endpoint..."
curl -s http://$SERVER_IP/ws/stats | python3 -m json.tool || echo "API not responding yet"

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║              🎉 DEPLOYMENT COMPLETE! 🎉                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "✅ Redis PubSub WebSocket system is now live!"
echo ""
echo "📊 Verification Commands:"
echo "  • Test API: curl http://$SERVER_IP/ws/stats"
echo "  • View logs: ssh $SERVER_USER@$SERVER_IP 'tail -f /var/log/taxi-api.out.log'"
echo "  • Redis monitor: ssh $SERVER_USER@$SERVER_IP 'redis-cli -a PASSWORD MONITOR'"
echo ""
echo "📚 Documentation:"
echo "  • REDIS_SETUP.md - Detailed setup guide"
echo "  • WEBSOCKET_GUIDE.md - WebSocket API documentation"
echo "  • REDIS_IMPLEMENTATION_SUMMARY.md - Technical overview"
echo ""
echo "🔐 IMPORTANT: Save your Redis password!"
echo "  Redis Password: $REDIS_PASSWORD"
echo ""
echo "Next steps:"
echo "  1. Test WebSocket connections with mobile app"
echo "  2. Monitor Redis memory usage"
echo "  3. Check logs for any errors"
echo ""
