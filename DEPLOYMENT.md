# Deployment Guide - Taxi Service Backend

## 🚀 Production Deployment

### Prerequisites
- Ubuntu Server 20.04+ or similar Linux distribution
- Domain name (e.g., api.taxiservice.uz)
- SSL certificate (Let's Encrypt recommended)
- PostgreSQL 12+
- Redis 6+
- Python 3.9+
- Nginx

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib redis-server

# Install supervisor for process management
sudo apt install -y supervisor
```

### Step 2: Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE taxi_db;
CREATE USER taxi_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE taxi_db TO taxi_user;
\q
```

### Step 3: Application Setup

```bash
# Create application directory
sudo mkdir -p /var/www/taxi-service
cd /var/www/taxi-service

# Clone repository or upload files
git clone <your-repo-url> .

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install gunicorn
pip install gunicorn

# Create .env file
cp .env.example .env
nano .env
```

**Edit .env with production values:**
```env
DATABASE_URL=postgresql://taxi_user:your_secure_password@localhost:5432/taxi_db
SECRET_KEY=your-very-long-random-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_ADMIN_GROUP_ID=your-admin-group-id
UPLOAD_DIR=/var/www/taxi-service/uploads
REDIS_URL=redis://localhost:6379/0
DEBUG=False
```

### Step 4: Database Migrations

```bash
# Run migrations
alembic upgrade head

# Seed initial data
python scripts/seed_data.py

# Create superadmin
python scripts/create_superadmin.py
```

### Step 5: Gunicorn Setup

Create `/etc/supervisor/conf.d/taxi-api.conf`:

```ini
[program:taxi-api]
command=/var/www/taxi-service/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 127.0.0.1:8000
directory=/var/www/taxi-service
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/taxi-api.err.log
stdout_logfile=/var/log/taxi-api.out.log
```

Create `/etc/supervisor/conf.d/taxi-user-bot.conf`:

```ini
[program:taxi-user-bot]
command=/var/www/taxi-service/venv/bin/python bot/user_bot.py
directory=/var/www/taxi-service
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/taxi-user-bot.err.log
stdout_logfile=/var/log/taxi-user-bot.out.log
```

Create `/etc/supervisor/conf.d/taxi-admin-bot.conf`:

```ini
[program:taxi-admin-bot]
command=/var/www/taxi-service/venv/bin/python bot/admin_bot.py
directory=/var/www/taxi-service
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/taxi-admin-bot.err.log
stdout_logfile=/var/log/taxi-admin-bot.out.log
```

```bash
# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update

# Start services
sudo supervisorctl start taxi-api
sudo supervisorctl start taxi-user-bot
sudo supervisorctl start taxi-admin-bot

# Check status
sudo supervisorctl status
```

### Step 6: Nginx Configuration

Create `/etc/nginx/sites-available/taxi-api`:

```nginx
server {
    listen 80;
    server_name api.taxiservice.uz;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /uploads {
        alias /var/www/taxi-service/uploads;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /static {
        alias /var/www/taxi-service/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/taxi-api /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### Step 7: SSL with Let's Encrypt

```bash
# Install certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d api.taxiservice.uz

# Auto-renewal is set up automatically
# Test renewal
sudo certbot renew --dry-run
```

### Step 8: Firewall Setup

```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Step 9: Redis Configuration

```bash
# Edit redis configuration
sudo nano /etc/redis/redis.conf

# Set password (uncomment and set)
# requirepass your_redis_password

# Restart redis
sudo systemctl restart redis-server

# Update .env with Redis password
REDIS_URL=redis://:your_redis_password@localhost:6379/0
```

### Step 10: Monitoring & Logs

```bash
# View API logs
sudo tail -f /var/log/taxi-api.out.log
sudo tail -f /var/log/taxi-api.err.log

# View bot logs
sudo tail -f /var/log/taxi-user-bot.out.log
sudo tail -f /var/log/taxi-admin-bot.out.log

# Supervisor logs
sudo supervisorctl tail -f taxi-api
```

## 📊 Performance Optimization

### PostgreSQL Tuning

Edit `/etc/postgresql/12/main/postgresql.conf`:

```conf
# Memory settings (for 4GB RAM)
shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
work_mem = 16MB

# Connection settings
max_connections = 100

# Logging
log_min_duration_statement = 1000  # Log slow queries (> 1s)
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

### Nginx Tuning

Edit `/etc/nginx/nginx.conf`:

```nginx
worker_processes auto;
worker_connections 1024;

# Enable gzip compression
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;
```

## 🔒 Security Checklist

- ✅ Change default superadmin password
- ✅ Use strong SECRET_KEY (at least 32 random characters)
- ✅ Enable firewall (UFW)
- ✅ Use SSL/TLS certificates
- ✅ Set Redis password
- ✅ Use strong database password
- ✅ Disable DEBUG mode in production
- ✅ Regular security updates
- ✅ Limit CORS origins
- ✅ Regular database backups
- ✅ Monitor logs for suspicious activity

## 💾 Backup Strategy

### Database Backup

Create `/usr/local/bin/backup-taxi-db.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/var/backups/taxi-db"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

pg_dump -U taxi_user taxi_db | gzip > $BACKUP_DIR/taxi_db_$DATE.sql.gz

# Keep only last 30 days
find $BACKUP_DIR -type f -mtime +30 -delete
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup-taxi-db.sh

# Add to crontab (daily at 2 AM)
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-taxi-db.sh
```

### Upload Files Backup

```bash
# Backup uploads directory
sudo tar -czf /var/backups/taxi-uploads-$(date +%Y%m%d).tar.gz /var/www/taxi-service/uploads
```

## 🔄 Updating the Application

```bash
# Navigate to application directory
cd /var/www/taxi-service

# Activate virtual environment
source venv/bin/activate

# Pull latest changes
git pull origin main

# Install/update dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Restart services
sudo supervisorctl restart taxi-api
sudo supervisorctl restart taxi-user-bot
sudo supervisorctl restart taxi-admin-bot
```

## 📈 Monitoring Tools (Optional)

### Install Prometheus & Grafana

```bash
# Install prometheus
sudo apt install -y prometheus

# Install grafana
sudo apt-get install -y software-properties-common
sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
sudo apt update
sudo apt install -y grafana

sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

## 🆘 Troubleshooting

### Service won't start

```bash
# Check supervisor logs
sudo supervisorctl tail taxi-api stderr

# Check permissions
sudo chown -R www-data:www-data /var/www/taxi-service

# Check Python environment
source /var/www/taxi-service/venv/bin/activate
python -c "import fastapi; print('OK')"
```

### Database connection issues

```bash
# Test database connection
psql -U taxi_user -d taxi_db -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql
```

### High memory usage

```bash
# Check running processes
ps aux | grep python

# Reduce gunicorn workers
# Edit supervisor config, reduce -w parameter
```

## 📞 Support

For production deployment support:
- Email: devops@taxiservice.uz
- Telegram: @taxiservice_support
