# =================================================================
# Use a Debian-based slim image for better pre-compiled package support
# =================================================================
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies using apt-get
# Pre-installing mupdf avoids the need for a separate builder stage
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python packages
# This will now be much faster as it should use a pre-compiled wheel
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code and language config
COPY process_pdfs.py .
COPY languages.json .

# Create a non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Create directories and set permissions
RUN mkdir -p /app/sample_datasets/pdfs /app/sample_datasets/outputs && \
    chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser

# Set default command arguments
CMD ["./sample_datasets/pdfs", "./sample_datasets/outputs", "--lang", "en"]

# Entrypoint to execute the script
ENTRYPOINT ["python", "process_pdfs.py"]