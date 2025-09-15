#!/bin/bash

# Quick Demo Test Script for Lightsail Deployment
# Run this to test your deployed API

set -e

# Get public IP (works on Lightsail)
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || curl -s https://ipinfo.io/ip)
BASE_URL="http://$PUBLIC_IP"

echo "🎯 Testing Dappier-Skyfire API Demo"
echo "=================================="
echo "Base URL: $BASE_URL"
echo ""

# Test 1: Health Check
echo "1️⃣  Health Check:"
curl -s "$BASE_URL/health" | python3 -m json.tool || echo "❌ Health check failed"
echo ""

# Test 2: Initialize
echo "2️⃣  Initialize System:"
curl -s -X POST "$BASE_URL/initialize" | python3 -m json.tool || echo "❌ Initialize failed"
echo ""

# Test 3: Create Session
echo "3️⃣  Create New Session:"
SESSION_RESPONSE=$(curl -s -X POST "$BASE_URL/sessions/new")
echo "$SESSION_RESPONSE" | python3 -m json.tool || echo "❌ Session creation failed"

# Extract session ID
SESSION_ID=$(echo "$SESSION_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('session_id', 'demo'))" 2>/dev/null || echo "demo")
echo "Session ID: $SESSION_ID"
echo ""

# Test 4: Simple Chat
echo "4️⃣  Test Chat (Simple):"
curl -s -X POST "$BASE_URL/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Hello, how are you?\", \"session_id\": \"$SESSION_ID\"}" \
  | head -c 500
echo "..."
echo ""

# Test 5: List Sessions
echo "5️⃣  List Sessions:"
curl -s "$BASE_URL/sessions" | python3 -m json.tool || echo "❌ List sessions failed"
echo ""

echo "✅ Demo test complete!"
echo ""
echo "🔗 Demo URLs for presentations:"
echo "   Health: $BASE_URL/health"
echo "   Initialize: curl -X POST $BASE_URL/initialize"
echo "   New Session: curl -X POST $BASE_URL/sessions/new"
echo "   Chat: curl -X POST $BASE_URL/chat -H 'Content-Type: application/json' -d '{\"message\":\"What is AI?\",\"session_id\":\"demo\"}'"