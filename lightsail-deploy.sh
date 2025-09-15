#!/bin/bash

# Lightsail Deployment Script for Dappier-Skyfire API
set -e

echo "🚀 Deploying Dappier-Skyfire API on AWS Lightsail"
echo "================================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running on Lightsail
check_environment() {
    print_status "Checking environment..."
    
    if [ ! -f "/etc/lightsail-release" ] && [ ! -f "/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json" ]; then
        print_warning "This doesn't appear to be a Lightsail instance, but continuing anyway..."
    fi
    
    print_success "Environment check complete"
}

# Check dependencies
check_dependencies() {
    print_status "Checking dependencies..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker not found. Installing..."
        sudo apt update
        sudo apt install -y docker.io docker-compose
        sudo systemctl start docker
        sudo systemctl enable docker
        sudo usermod -aG docker $USER
        print_warning "Please logout and login again, then re-run this script"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose not found. Installing..."
        sudo apt install -y docker-compose
    fi
    
    print_success "Dependencies check complete"
}

# Setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_warning "Created .env from .env.example"
            print_warning "Please edit .env with your API keys: nano .env"
            read -p "Press Enter after updating .env file..."
        else
            print_error ".env file not found. Creating template..."
            cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key_here
SKYFIRE_API_KEY=your_skyfire_api_key_here
SKYFIRE_SELLER_API_KEY=your_skyfire_seller_api_key_here
EOF
            print_warning "Please edit .env with your API keys: nano .env"
            read -p "Press Enter after updating .env file..."
        fi
    fi
    
    print_success "Environment setup complete"
}

# Deploy application
deploy_app() {
    print_status "Deploying application..."
    
    # Stop existing containers
    docker-compose down || true
    
    # Build and start
    print_status "Building Docker image..."
    docker-compose build --no-cache
    
    print_status "Starting services..."
    docker-compose up -d
    
    # Wait for health check
    print_status "Waiting for application to be ready..."
    max_attempts=30
    attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:5000/health > /dev/null 2>&1; then
            print_success "Application is healthy!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Application failed to start"
            docker-compose logs
            exit 1
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
}

# Setup Nginx reverse proxy
setup_nginx() {
    print_status "Setting up Nginx reverse proxy..."
    
    # Install Nginx if not present
    if ! command -v nginx &> /dev/null; then
        sudo apt install -y nginx
    fi
    
    # Get public IP
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || curl -s https://ipinfo.io/ip)
    
    # Create Nginx config
    sudo tee /etc/nginx/sites-available/dappier-skyfire-api << EOF
server {
    listen 80;
    server_name $PUBLIC_IP _;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # Increase timeout for streaming responses
    proxy_read_timeout 600s;
    proxy_connect_timeout 60s;
    proxy_send_timeout 600s;
    proxy_buffering off;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # CORS headers
        add_header Access-Control-Allow-Origin *;
        add_header Access-Control-Allow-Methods "GET, POST, DELETE, OPTIONS";
        add_header Access-Control-Allow-Headers "Content-Type, Authorization";
        
        # Handle preflight requests
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin *;
            add_header Access-Control-Allow-Methods "GET, POST, DELETE, OPTIONS";
            add_header Access-Control-Allow-Headers "Content-Type, Authorization";
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 200;
        }
    }
}
EOF

    # Enable site
    sudo ln -sf /etc/nginx/sites-available/dappier-skyfire-api /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload Nginx
    sudo nginx -t && sudo systemctl reload nginx
    sudo systemctl enable nginx
    
    print_success "Nginx configured and running"
}

# Setup auto-start service
setup_autostart() {
    print_status "Setting up auto-start service..."
    
    sudo tee /etc/systemd/system/dappier-skyfire-api.service << EOF
[Unit]
Description=Dappier Skyfire API
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
User=ubuntu
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable dappier-skyfire-api.service
    
    print_success "Auto-start service configured"
}

# Show deployment info
show_deployment_info() {
    PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || curl -s https://ipinfo.io/ip)
    
    echo ""
    echo "🎉 Deployment Complete!"
    echo "======================"
    echo ""
    echo "📍 Your API is available at:"
    echo "   Public URL: http://$PUBLIC_IP"
    echo "   Direct API: http://$PUBLIC_IP:5000"
    echo ""
    echo "🔗 Demo Endpoints:"
    echo "   Health:     curl http://$PUBLIC_IP/health"
    echo "   Initialize: curl -X POST http://$PUBLIC_IP/initialize"
    echo "   New Session: curl -X POST http://$PUBLIC_IP/sessions/new"
    echo "   Chat:       curl -X POST http://$PUBLIC_IP/chat -H 'Content-Type: application/json' -d '{\"message\":\"Hello\",\"session_id\":\"demo\"}'"
    echo ""
    echo "🛠️  Management Commands:"
    echo "   View logs:    docker-compose logs -f"
    echo "   Restart:      docker-compose restart"
    echo "   Stop:         docker-compose down"
    echo "   Status:       docker-compose ps"
    echo ""
    echo "📊 Quick Test:"
    curl -s http://localhost:5000/health | python3 -m json.tool 2>/dev/null || echo "Starting up..."
    echo ""
}

# Main execution
main() {
    check_environment
    check_dependencies
    setup_environment
    deploy_app
    setup_nginx
    setup_autostart
    show_deployment_info
    
    print_success "Dappier-Skyfire API is now running on Lightsail!"
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "start")
        docker-compose up -d
        print_success "Services started"
        ;;
    "stop")
        docker-compose down
        print_success "Services stopped"
        ;;
    "restart")
        docker-compose restart
        print_success "Services restarted"
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "status")
        docker-compose ps
        echo ""
        curl -s http://localhost:5000/health | python3 -m json.tool 2>/dev/null || echo "API not responding"
        ;;
    "update")
        print_status "Updating application..."
        git pull || print_warning "Not a git repository, skipping git pull"
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        print_success "Update complete"
        ;;
    *)
        echo "Usage: $0 {deploy|start|stop|restart|logs|status|update}"
        exit 1
        ;;
esac