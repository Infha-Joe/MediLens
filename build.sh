#!/usr/bin/env bash
# Render build script

# Install system packages from Aptfile
if [ -f Aptfile ]; then
  apt-get update && apt-get install -y $(cat Aptfile)
fi

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
