#!/bin/bash
# ============================================================================
# Lucifex Agent One-Line Installer
# ============================================================================
#
# Usage (remotely):
#   curl -fsSL https://raw.githubusercontent.com/Gabrie-yx/lucifexia/main/install.sh | bash
#
# Usage (locally):
#   ./install.sh
#
# ============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}⚕ Starting Lucifex Agent installation...${NC}"

# 1. Determine installation directory
if [ -f "./setup-lucifex.sh" ]; then
    INSTALL_DIR="$(pwd)"
    echo -e "${GREEN}✓${NC} Local clone detected: $INSTALL_DIR"
else
    INSTALL_DIR="$HOME/.lucifex/lucifex-agent"
    echo -e "${CYAN}→${NC} Target directory: $INSTALL_DIR"
    
    # Check if git is installed
    if ! command -v git &>/dev/null; then
        echo -e "${RED}✗${NC} git is required but not installed. Please install git and retry."
        exit 1
    fi
    
    # Clone or pull updates
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${CYAN}→${NC} Directory already exists, updating repo..."
        cd "$INSTALL_DIR"
        git pull
    else
        echo -e "${CYAN}→${NC} Cloning repository..."
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone https://github.com/Gabrie-yx/lucifexia.git "$INSTALL_DIR"
        cd "$INSTALL_DIR"
    fi
fi

# 2. Make setup script executable and run it
if [ -f "./setup-lucifex.sh" ]; then
    chmod +x ./setup-lucifex.sh
    ./setup-lucifex.sh
else
    echo -e "${RED}✗${NC} setup-lucifex.sh not found in the target directory."
    exit 1
fi
