# ==========================
# Dockerfile para Flask + dlib + OpenCV + MySQL + Excel
# ==========================
FROM python:3.9-slim

# --------------------------
# Instalar dependencias del sistema necesarias
# --------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk2.0-dev \
    libboost-all-dev \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    zlib1g-dev \
    libgl1 \
    libglib2.0-0 \
    libffi-dev \
    libsm6 \
    libxrender1 \
    libxext6 \
    wget \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# --------------------------
# Crear entorno virtual
# --------------------------
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# --------------------------
# Copiar e instalar requerimientos
# --------------------------
COPY requirements.txt /app/
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r /app/requirements.txt

# --------------------------
# Copiar el código fuente
# --------------------------
COPY . /app/
WORKDIR /app

# --------------------------
# Comando para iniciar la app con Gunicorn
# 4 workers, puerto dinámico Railway
# --------------------------
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--workers", "4", "app:app"]