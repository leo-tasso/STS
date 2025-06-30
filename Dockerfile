FROM ubuntu:22.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies and Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    wget \
    curl \
    unzip \
    tar \
    ca-certificates \
    dos2unix \
    git \
    libgl1-mesa-glx \
    libegl1-mesa \
    libxrandr2 \
    libxss1 \
    libxcursor1 \
    libxcomposite1 \
    libasound2 \
    libxi6 \
    libxtst6 \
    libglib2.0-0 \
    libgtk-3-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create symbolic links for python and pip
RUN ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Download and install MiniZinc 2.9.3
RUN cd /tmp && \
    wget -q https://github.com/MiniZinc/MiniZincIDE/releases/download/2.9.3/MiniZincIDE-2.9.3-bundle-linux-x86_64.tgz && \
    tar -xzf MiniZincIDE-2.9.3-bundle-linux-x86_64.tgz && \
    mv MiniZincIDE-2.9.3-bundle-linux-x86_64 /opt/minizinc && \
    chmod -R +x /opt/minizinc/bin/ && \
    rm -f MiniZincIDE-2.9.3-bundle-linux-x86_64.tgz

# Set environment variables
ENV PATH="/opt/minizinc/bin:${PATH}"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1
ENV CVC5_BIN="/app/source/SMT/cvc5/bin/cvc5"

# Create app directory and set as working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Convert Windows line endings to Unix for MiniZinc files
RUN find . -type f \( -name "*.mzn" -o -name "*.dzn" \) -exec dos2unix {} \;

# Create results directories
RUN mkdir -p res/CP res/SAT

# Verify installations
RUN python --version && \
    pip --version && \
    minizinc --version && \
    minizinc --solvers

# Set default command
CMD ["/bin/bash"]
