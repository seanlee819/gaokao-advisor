#!/bin/bash
# 高考志愿推荐 — 云服务器一键部署脚本
# 适用: Ubuntu 20.04+ / CentOS 7+ 
# 用法: bash deploy.sh

set -e
APP_DIR="/opt/gaokao-advisor"
DOMAIN="${1:-your-domain.com}"

echo "========================================"
echo "  高考志愿推荐 — 服务器部署"
echo "  Domain: $DOMAIN"
echo "========================================"

# 1. 安装依赖
echo "[1/6] 安装系统依赖..."
apt-get update -qq && apt-get install -y -qq python3 python3-pip nginx certbot python3-certbot-nginx 2>/dev/null || \
yum install -y python3 python3-pip nginx 2>/dev/null

# 2. 部署应用
echo "[2/6] 部署应用..."
mkdir -p $APP_DIR
cp -r . $APP_DIR/
cd $APP_DIR
pip3 install -r requirements.txt fastapi uvicorn -q

# 3. 创建 systemd 服务
echo "[3/6] 配置服务..."
cat > /etc/systemd/system/gaokao-api.service << EOF
[Unit]
Description=Gaokao Advisor API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 $APP_DIR/server.py --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/gaokao-web.service << EOF
[Unit]
Description=Gaokao Advisor Web
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/python3 -m streamlit run $APP_DIR/app.py --server.port 8501 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable gaokao-api gaokao-web
systemctl start gaokao-api gaokao-web

# 4. Nginx
echo "[4/6] 配置 Nginx..."
cat > /etc/nginx/sites-available/gaokao << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 120s;
    }

    # Web
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 120s;
    }

    client_max_body_size 50M;
}
EOF

ln -sf /etc/nginx/sites-available/gaokao /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# 5. SSL
echo "[5/6] 配置 SSL..."
certbot --nginx -d $DOMAIN --non-interactive --agree-tos -m admin@$DOMAIN 2>/dev/null || \
echo "  SSL 跳过 (域名未解析或 certbot 不可用), HTTP 模式运行"

# 6. 防火墙
echo "[6/6] 配置防火墙..."
ufw allow 80/tcp 2>/dev/null || true
ufw allow 443/tcp 2>/dev/null || true
ufw allow 22/tcp 2>/dev/null || true

echo ""
echo "========================================"
echo "  部署完成!"
echo "  API:  https://$DOMAIN/api/health"
echo "  Web:  https://$DOMAIN"
echo "  Docs: https://$DOMAIN/api/docs"
echo "========================================"
