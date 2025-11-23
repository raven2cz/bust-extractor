FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements_advanced.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_advanced.txt

# Copy the extractor script
COPY bust_extractor_advanced.py .

# Create directories for input/output
RUN mkdir -p /input /output

# Set volumes for input and output
VOLUME ["/input", "/output"]

# Set the entrypoint
ENTRYPOINT ["python", "bust_extractor_advanced.py"]

# Default help command
CMD ["--help"]
