# Use a Debian-based image for better Selenium compatibility
FROM debian:stable-slim

# Set environment variables for non-interactive apt-get
ENV DEBIAN_FRONTEND=noninteractive

# Switch to root to install packages
USER root

# Update package lists and install necessary packages
# This includes Python, pip, LibreOffice, and other dependencies for headless Chrome
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    libreoffice \
    chromium chromium-driver \
    fonts-freefont-ttf \
    fonts-noto-cjk \
    libharfbuzz0b \
    libgl1-mesa-dri \
    libglx-mesa0 \
    dbus \
    libnss3 \
    libfreetype6 \
    libgcc-s1 \
    libstdc++6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxrender1 \
    libfontconfig1 \
    libgomp1 \
    xvfb \
    xauth \
    wget unzip \
    && rm -rf /var/lib/apt/lists/*

# Create a non-privileged user 'worker'
RUN useradd -ms /bin/bash worker

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
# This allows Docker to cache the dependency installation step
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Switch to the non-privileged user
USER worker

# The main command to run when the container launches.
# This will execute the script from the volume you mount at /app.
ENTRYPOINT ["/bin/bash", "run_crawlers.sh"]