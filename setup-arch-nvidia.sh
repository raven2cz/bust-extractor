#!/bin/bash

# =============================================================================
# Bust Extractor Pro - Arch Linux Setup Script
# =============================================================================
# Version: 1.0
# Supports: NVIDIA CUDA / CPU fallback
# Shells: bash, zsh, fish, csh/tcsh
#
# Usage:
#   chmod +x setup-arch.sh
#   ./setup-arch.sh
# =============================================================================

set -e

# Configuration
VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"
PYTHON_VERSION="3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Helper functions
print_header() { echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════════════${NC}"; echo -e "${BOLD}${CYAN}  $1${NC}"; echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════${NC}\n"; }
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_success() { echo -e "${GREEN}[OK]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

print_header "🎨 Bust Extractor Pro - Arch Linux Setup"

# =============================================================================
# 1. System Detection
# =============================================================================
print_info "Detecting system configuration..."

# Architecture check
ARCH=$(uname -m)
print_info "Architecture: $ARCH"

if [[ "$ARCH" != "x86_64" ]]; then
    print_warn "Non-x86_64 architecture detected. PyTorch wheels may be limited."
fi

# Shell detection
CURRENT_SHELL=$(basename "$SHELL")
print_info "Default shell: $CURRENT_SHELL"

case "$CURRENT_SHELL" in
    fish)
        ACTIVATE_CMD="source $VENV_DIR/bin/activate.fish"
        ;;
    csh|tcsh)
        ACTIVATE_CMD="source $VENV_DIR/bin/activate.csh"
        ;;
    *)
        ACTIVATE_CMD="source $VENV_DIR/bin/activate"
        ;;
esac

# GPU detection
print_info "Detecting GPU..."
MODE="cpu"

if command -v nvidia-smi &> /dev/null; then
    if nvidia-smi &> /dev/null; then
        CUDA_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
        print_success "NVIDIA GPU detected (Driver: $CUDA_VERSION)"
        MODE="cuda"
    else
        print_warn "nvidia-smi found but GPU not accessible. Using CPU mode."
    fi
else
    print_warn "NVIDIA GPU not found. Using CPU mode."
fi

# =============================================================================
# 2. Install uv (if not present)
# =============================================================================
print_header "📦 Package Manager Setup"

if ! command -v uv &> /dev/null; then
    print_info "Installing 'uv' package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    
    # Update PATH for current session
    export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
    
    if ! command -v uv &> /dev/null; then
        print_error "Failed to install uv. Please install manually:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
fi

print_success "uv version: $(uv --version)"

# =============================================================================
# 3. Create Virtual Environment
# =============================================================================
print_header "🐍 Python Environment"

print_info "Creating virtual environment with Python $PYTHON_VERSION..."

# Remove old venv if exists (avoid prompts)
if [ -d "$VENV_DIR" ]; then
    print_info "Removing existing virtual environment..."
    rm -rf "$VENV_DIR"
fi

# Create new venv with uv
uv venv "$VENV_DIR" --python "$PYTHON_VERSION" --seed

if [ ! -d "$VENV_DIR" ]; then
    print_error "Failed to create virtual environment!"
    exit 1
fi

print_success "Virtual environment created at $VENV_DIR"

# Verify Python in venv
VENV_PYTHON="$VENV_DIR/bin/python"
PYTHON_FULL_VERSION=$("$VENV_PYTHON" --version 2>&1)
print_info "Python version: $PYTHON_FULL_VERSION"

# =============================================================================
# 4. Install Dependencies
# =============================================================================
print_header "📥 Installing Dependencies"

# Upgrade pip first (using uv pip for reliability)
print_info "Upgrading pip, setuptools, wheel..."
uv pip install --python "$VENV_PYTHON" --upgrade pip setuptools wheel

# Clean any conflicting packages
print_info "Cleaning potential conflicts..."
uv pip uninstall --python "$VENV_PYTHON" onnxruntime onnxruntime-gpu 2>/dev/null || true

# Install PyTorch based on mode
if [ "$MODE" == "cuda" ]; then
    print_info "Installing PyTorch with CUDA 12.1 support..."
    
    # Try CUDA 12.1 first, fallback to CUDA 12.4 if needed
    if uv pip install --python "$VENV_PYTHON" torch torchvision \
        --index-url https://download.pytorch.org/whl/cu121; then
        print_success "PyTorch (CUDA 12.1) installed successfully"
    else
        print_warn "CUDA 12.1 failed, trying CUDA 12.4..."
        if uv pip install --python "$VENV_PYTHON" torch torchvision \
            --index-url https://download.pytorch.org/whl/cu124; then
            print_success "PyTorch (CUDA 12.4) installed successfully"
        else
            print_warn "Specific CUDA version failed, falling back to PyPI..."
            uv pip install --python "$VENV_PYTHON" torch torchvision
        fi
    fi
    
    # Install GPU-accelerated ONNX Runtime
    print_info "Installing ONNX Runtime (GPU)..."
    uv pip install --python "$VENV_PYTHON" onnxruntime-gpu || \
        print_warn "GPU ONNX Runtime failed, will use CPU version"
else
    print_info "Installing PyTorch (CPU only)..."
    
    # Strategy: Try CPU-specific index first, then PyPI fallback
    TORCH_INSTALLED=false
    
    # Attempt 1: CPU-specific wheels (smaller download)
    print_info "Trying CPU-optimized wheels..."
    if uv pip install --python "$VENV_PYTHON" torch torchvision \
        --index-url https://download.pytorch.org/whl/cpu 2>/dev/null; then
        print_success "PyTorch (CPU-optimized) installed successfully"
        TORCH_INSTALLED=true
    fi
    
    # Attempt 2: Standard PyPI (larger but more compatible)
    if [ "$TORCH_INSTALLED" = false ]; then
        print_warn "CPU index failed. Trying standard PyPI..."
        if uv pip install --python "$VENV_PYTHON" torch torchvision; then
            print_success "PyTorch installed from PyPI"
            TORCH_INSTALLED=true
        fi
    fi
    
    # Attempt 3: Specific version that's known to work
    if [ "$TORCH_INSTALLED" = false ]; then
        print_warn "Standard install failed. Trying specific version..."
        if uv pip install --python "$VENV_PYTHON" "torch==2.2.0" "torchvision==0.17.0"; then
            print_success "PyTorch 2.2.0 installed"
            TORCH_INSTALLED=true
        fi
    fi
    
    if [ "$TORCH_INSTALLED" = false ]; then
        print_error "Failed to install PyTorch!"
        print_info "Possible solutions:"
        echo "  1. Check your internet connection"
        echo "  2. Try: uv pip install --python $VENV_PYTHON torch torchvision"
        echo "  3. Check PyTorch compatibility: https://pytorch.org/get-started/locally/"
        exit 1
    fi
    
    # Install CPU ONNX Runtime
    print_info "Installing ONNX Runtime (CPU)..."
    uv pip install --python "$VENV_PYTHON" onnxruntime
fi

# Install project requirements
if [ -f "$REQUIREMENTS_FILE" ]; then
    print_info "Installing project requirements from $REQUIREMENTS_FILE..."
    
    # Create temp requirements without torch (already installed)
    grep -v "^torch" "$REQUIREMENTS_FILE" | grep -v "^onnxruntime" > /tmp/requirements_filtered.txt || true
    
    if [ -s /tmp/requirements_filtered.txt ]; then
        uv pip install --python "$VENV_PYTHON" -r /tmp/requirements_filtered.txt
    fi
    
    rm -f /tmp/requirements_filtered.txt
    print_success "Project requirements installed"
else
    print_warn "No $REQUIREMENTS_FILE found, skipping..."
fi

# =============================================================================
# 5. Verification
# =============================================================================
print_header "✅ Verification"

print_info "Checking installations..."

# Python packages verification
"$VENV_PYTHON" << 'EOF'
import sys

def check_import(name, display_name=None):
    display = display_name or name
    try:
        module = __import__(name)
        version = getattr(module, '__version__', 'unknown')
        print(f"  ✓ {display}: {version}")
        return True
    except ImportError as e:
        print(f"  ✗ {display}: NOT INSTALLED ({e})")
        return False

print("Python packages:")
check_import('torch', 'PyTorch')
check_import('torchvision', 'TorchVision')
check_import('PIL', 'Pillow')
check_import('numpy', 'NumPy')
check_import('cv2', 'OpenCV')
check_import('fastapi', 'FastAPI')
check_import('rembg', 'rembg')

# CUDA check
import torch
print(f"\nCUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA version: {torch.version.cuda}")
    print(f"GPU: {torch.cuda.get_device_name(0)}")
EOF

# =============================================================================
# 6. Final Instructions
# =============================================================================
print_header "🚀 Setup Complete!"

echo -e "${GREEN}Environment is ready!${NC}\n"

echo -e "To activate the virtual environment, run:"
echo -e "  ${BOLD}${CYAN}$ACTIVATE_CMD${NC}\n"

echo -e "To start the application:"
echo -e "  ${BOLD}${CYAN}python run.py${NC}\n"

echo -e "Or run directly without activation:"
echo -e "  ${BOLD}${CYAN}$VENV_PYTHON run.py${NC}\n"

# Fish-specific tip
if [ "$CURRENT_SHELL" = "fish" ]; then
    echo -e "${YELLOW}Fish shell tip:${NC}"
    echo -e "  Add to ~/.config/fish/config.fish for convenience:"
    echo -e "  ${CYAN}alias bust-extractor='cd $(pwd) && source .venv/bin/activate.fish && python run.py'${NC}\n"
fi

print_success "Happy extracting! 🎨"
