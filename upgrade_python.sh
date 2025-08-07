#!/bin/bash

echo "========================================="
echo "Upgrading Python Environment to 3.11"
echo "========================================="

# Step 1: Install Python 3.11 via Homebrew
echo "Step 1: Installing Python 3.11..."
brew install python@3.11

# Step 2: Check installation
echo -e "\nStep 2: Verifying Python 3.11 installation..."
python3.11 --version

# Step 3: Backup current requirements
echo -e "\nStep 3: Backing up current requirements..."
source venv/bin/activate
pip freeze > requirements_backup.txt
deactivate

# Step 4: Remove old venv and create new one with Python 3.11
echo -e "\nStep 4: Creating new virtual environment with Python 3.11..."
rm -rf venv_old
mv venv venv_old
python3.11 -m venv venv

# Step 5: Activate new venv and upgrade pip
echo -e "\nStep 5: Upgrading pip..."
source venv/bin/activate
python -m pip install --upgrade pip

# Step 6: Install requirements
echo -e "\nStep 6: Installing packages..."
pip install -r requirements.txt

# Step 7: Install additional packages that might not be in requirements.txt
echo -e "\nStep 7: Installing additional packages..."
pip install pytest pytest-asyncio

# Step 8: Verify installation
echo -e "\nStep 8: Verification..."
echo "Python version in new venv:"
python --version

echo -e "\nTesting imports..."
python -c "
import alpaca_trade_api
import pandas
import numpy
from src.strategies import EarlyDetectionIntegration, SocialIntegration, UltimateTradingStrategy
print('✅ All critical imports working!')
"

echo -e "\n========================================="
echo "✅ Upgrade Complete!"
echo "========================================="
echo "New environment: Python $(python --version)"
echo "Old environment backed up to: venv_old/"
echo ""
echo "To activate the new environment:"
echo "  source venv/bin/activate"
echo ""
echo "If something went wrong, restore old environment:"
echo "  rm -rf venv && mv venv_old venv"
echo "========================================="