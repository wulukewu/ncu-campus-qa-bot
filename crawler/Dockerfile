# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install system dependencies for file conversion
# pandoc is for converting documents (used by pypandoc)
# weasyprint dependencies are for converting HTML to PDF
# texlive-* and fonts-* are for pandoc to create PDFs with Chinese characters
RUN apt-get update && apt-get install -y \
    pandoc \
    libpango-1.0-0 \
    libharfbuzz0b \
    libfontconfig1 \
    libcairo2 \
    # Added for pandoc CJK PDF support
    texlive-xetex \
    texlive-luatex \
    texlive-lang-cjk \
    fonts-wqy-zenhei \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
# This allows Docker to cache the dependency installation step
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# The main command to run when the container launches.
# This will execute the script from the volume you mount at /app.
CMD ["/bin/bash", "run_crawlers.sh"]
