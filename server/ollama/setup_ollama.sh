#!/bin/sh

ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama server to start..."
until curl -s http://localhost:11434/api/tags > /dev/null; do
    echo "Ollama server not yet available, retrying in 1 second..."
    sleep 1
done
echo "Ollama server started."

ollama pull qwen3-embedding:0.6b

wait $OLLAMA_PID