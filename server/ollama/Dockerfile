FROM ollama/ollama

# Install curl
RUN apt-get update && apt-get install -y curl

# Copy the setup script into the container
COPY setup_ollama.sh /usr/local/bin/setup_ollama.sh

# Make the script executable
RUN chmod +x /usr/local/bin/setup_ollama.sh

# Set the entrypoint to our setup script
ENTRYPOINT ["/usr/local/bin/setup_ollama.sh"]
