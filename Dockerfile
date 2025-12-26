FROM python:3.9-slim

# ------------------ Dependencias del sistema ------------------
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
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ------------------ Crear entorno virtual ------------------
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# ------------------ Copiar requerimientos e instalar ------------------
COPY requirements.txt /app/
WORKDIR /app
RUN pip install --upgrade pip setuptools wheel
RUN pip install -r requirements.txt --timeout=120

# ------------------ Copiar código fuente ------------------
COPY . /app/

# ------------------ Comando de producción ------------------
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app", "--workers=2", "--timeout=120"]
