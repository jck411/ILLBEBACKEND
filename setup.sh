#!/bin/bash

# Setup script for LLM Backend

echo "Setting up LLM Backend..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it first:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
uv venv

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
uv sync --strict

# Install development dependencies
echo "Installing development dependencies..."
uv add --dev pre-commit
uv run pre-commit install

# Copy environment file
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cp .env.example .env
    echo "Please edit .env and add your OpenAI API key"
fi

echo "Setup complete!"
echo ""
echo "To run the server:"
echo "  source .venv/bin/activate"
echo "  uv run python -m src.main"
echo ""
echo "Or simply:"
echo "  uv run python -m src.main"
