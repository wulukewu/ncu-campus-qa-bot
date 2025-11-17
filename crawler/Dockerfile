# Use the unoconv image which has libreoffice pre-installed
FROM ghcr.io/unoconv/unoserver-docker

# Switch to root to install packages
USER root

# Install python and pip
RUN apk add --no-cache python3 py3-pip

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
# This allows Docker to cache the dependency installation step
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Switch back to a non-privileged user
USER worker

# The main command to run when the container launches.
# This will execute the script from the volume you mount at /app.
ENTRYPOINT ["/bin/bash", "run_crawlers.sh"]
