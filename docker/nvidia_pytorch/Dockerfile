# Base image with PyTorch 2.4.0, CUDA 12.5, and Python 3.10
FROM nvcr.io/nvidia/pytorch:24.07-py3

# Set environment variables to optimize performance
ENV DEBIAN_FRONTEND=noninteractive \
    TORCH_CUDNN_V8_API_ENABLED=1 \
    PYTHONUNBUFFERED=1

# Upgrade pip and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Set the working directory inside the container
WORKDIR /workspace
