FROM python:3.9-slim

# Instalar dependencias del sistema necesarias
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Crear un entorno virtual
RUN python -m venv /opt/venv

# Activar entorno virtual e instalar deps
COPY requirements.txt /app/
RUN /opt/venv/bin/pip install --upgrade pip setuptools && /opt/venv/bin/pip install -r /app/requirements.txt

# Copiar código
COPY . /app/
WORKDIR /app

# Usar entorno virtual
ENV PATH="/opt/venv/bin:$PATH"

# Usar gunicorn para arrancar la app en Railway
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:$PORT"]