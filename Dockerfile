# Dockerfile - CRI Metrics System
FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar codigo fuente
COPY app/ ./app/
COPY static/ ./static/
COPY pytest.ini .
COPY tests/ ./tests/
COPY demo.py .
COPY demo_real.py .
COPY PLAN_IMPLANTACION.md .

# Variable de entorno por defecto
ENV DATABASE_URL=sqlite:///./cri_metrics.db
ENV PYTHONUNBUFFERED=1

# Puerto
EXPOSE 8000

# Comando de inicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
