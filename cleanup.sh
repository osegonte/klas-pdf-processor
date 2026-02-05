#!/bin/bash
# KLAS PDF Parser - Cleanup Script

echo "🧹 Cleaning up KLAS PDF Parser..."

# Remove UI files
echo "Removing UI files..."
rm -f app.py

# Remove old/unused files
echo "Removing unused files..."
rm -f main.py
rm -rf src/ai/
rm -rf src/models/

# Remove test outputs
echo "Cleaning output directories..."
rm -rf output/tmp*
rm -rf data/output/tmp*

# Keep data/input for user PDFs
mkdir -p data/input

echo "✅ Cleanup complete!"
echo ""
echo "📁 Clean structure:"
tree -L 2 -I 'venv|__pycache__|*.pyc|.git'
