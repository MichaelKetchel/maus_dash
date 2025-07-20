#!/usr/bin/env bash

cd backend
uv venv && source .venv/bin/activate
uv pip install -e .

# Start Redis (required for event bus)
docker run -d -p 6379:6379 redis:latest

# Start FastAPI server
python main.py