# Use a stable Python base
FROM python:3.10-slim-bullseye

# Avoid Python .pyc files & force stdout logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for Essentia & Python deps
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    wget \
    libfftw3-dev \
    libsamplerate0-dev \
    libtag1-dev \
    libyaml-dev \
    libeigen3-dev \
    libchromaprint-dev \
    libavcodec-dev \
    libavformat-dev \
    libavutil-dev \
    libswresample-dev \
    ffmpeg \
 && apt-get clean && rm -rf /var/lib/apt/lists/*


# Pre-install numpy (Essentia needs it to build Python bindings)
RUN pip install numpy

# Build Essentia from source
RUN git clone https://github.com/MTG/essentia.git /essentia && \
    cd /essentia && \
    python3 waf configure --with-python && \
    python3 waf build && \
    python3 waf install && \
    rm -rf /essentia

# Let system know where to find libessentia.so
ENV LD_LIBRARY_PATH=/usr/local/lib

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/

# Install project Python dependencies first
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy all your project files into the image
COPY . /app

# Expose FastAPI port
EXPOSE 8000

# Start the app with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]