#!/bin/bash

# USB to Google Drive Audio Sync System - Setup Script
# This script sets up the development environment and configures the system

set -e  # Exit on error

echo "=========================================="
echo "USB to Google Drive Audio Sync Setup"
echo "=========================================="
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This system is designed for macOS only."
    exit 1
fi

# Check Python version
echo "🔍 Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.9"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python $PYTHON_VERSION found, but Python $REQUIRED_VERSION or higher is required."
    exit 1
fi
echo "✅ Python $PYTHON_VERSION found"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo ""
echo "📦 Upgrading pip..."
pip install --upgrade pip --quiet

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✅ Dependencies installed"

# Create directory structure
echo ""
echo "📁 Creating directory structure..."
mkdir -p src/utils
mkdir -p config/credentials
mkdir -p logs
mkdir -p tests
echo "✅ Directory structure created"

# Copy settings file if it doesn't exist
echo ""
echo "⚙️  Setting up configuration..."
if [ ! -f "config/settings.json" ]; then
    cp config/settings.json.example config/settings.json
    echo "✅ Created settings.json from example"
    echo "⚠️  Please edit config/settings.json with your configuration"
else
    echo "✅ settings.json already exists"
fi

# Check for Google credentials
echo ""
echo "🔑 Checking Google Drive credentials..."
if [ ! -f "config/credentials/credentials.json" ]; then
    echo "⚠️  Google Drive credentials not found!"
    echo ""
    echo "Please follow these steps:"
    echo "1. Go to https://console.cloud.google.com/"
    echo "2. Create a new project or select existing"
    echo "3. Enable Google Drive API"
    echo "4. Create OAuth 2.0 credentials"
    echo "5. Download credentials.json"
    echo "6. Place it in config/credentials/"
    echo ""
else
    echo "✅ Google Drive credentials found"
fi

# Create LaunchAgent plist for auto-start
echo ""
echo "🚀 Setting up auto-start configuration..."
PLIST_PATH="$HOME/Library/LaunchAgents/com.user.usb-gdrive-sync.plist"
CURRENT_DIR=$(pwd)

cat > com.user.usb-gdrive-sync.plist.tmp << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.usb-gdrive-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>$CURRENT_DIR/venv/bin/python</string>
        <string>$CURRENT_DIR/src/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$CURRENT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$CURRENT_DIR/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>$CURRENT_DIR/logs/stderr.log</string>
</dict>
</plist>
EOF

echo "✅ LaunchAgent configuration created"
echo "   To enable auto-start, run:"
echo "   cp com.user.usb-gdrive-sync.plist.tmp $PLIST_PATH"
echo "   launchctl load $PLIST_PATH"

# Final instructions
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit config/settings.json with your configuration"
echo "2. Add Google Drive credentials to config/credentials/"
echo "3. Test the system: python src/main.py"
echo "4. Enable auto-start (optional) using LaunchAgent"
echo ""
echo "For more information, see README.md"
