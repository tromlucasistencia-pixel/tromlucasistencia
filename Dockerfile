# Usa Python 3.10 para mejor compatibilidad con dlib
FROM python:3.10-slim

# 1. Instalar dependencias del sistema (tal cual las tenías, están perfectas)
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

# 2. Configurar el directorio de trabajo
WORKDIR /app

# 3. Instalar requerimientos (Sin entorno virtual para simplificar en Docker)
# Nota: En Docker el contenedor ya está aislado, no hace falta venv
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copiar el resto del código
COPY . .

# 5. Crear carpetas de fotos para evitar errores de escritura
RUN mkdir -p fotos/entrada fotos/salida && chmod -R 777 fotos

# 6. COMANDO DE ARRANQUE CORREGIDO
# Cambiamos a formato de cadena para que $PORT funcione y bajamos workers a 2
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app