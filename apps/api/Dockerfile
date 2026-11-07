# Contexto de build: raíz del repo (necesita packages/ y data/).
#   docker build -f apps/api/Dockerfile -t predictions-api .
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY apps/api/requirements.txt /tmp/requirements.txt
# CA opcional para redes con proxy TLS (secret "extra_ca"); no queda en la imagen.
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export PIP_CERT=/run/secrets/extra_ca; fi; \
    pip install -r /tmp/requirements.txt

COPY packages ./packages
COPY data ./data
COPY apps/api ./apps/api

RUN useradd --create-home --uid 10001 app && chown -R app:app /app/data
USER app

WORKDIR /app/apps/api
ENV ENVIRONMENT=production \
    TRUST_PROXY_HEADERS=true \
    PORT=8000

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/health', timeout=4)"

# Un solo proceso por contenedor (el limitador y la caché viven en memoria).
# Escala con réplicas detrás del balanceador.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
