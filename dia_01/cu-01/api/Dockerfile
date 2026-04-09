FROM python:3.11-slim-bookworm

LABEL org.opencontainers.image.title="CU-01 Azure Service Recommender API" \
      org.opencontainers.image.version="2.0.0" \
      org.opencontainers.image.description="watsonx Orchestrate agent backend for Azure service recommendation"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN useradd -m appuser
USER appuser
WORKDIR /home/appuser/app

ENV PATH="/home/appuser/.local/bin:${PATH}"

COPY --chown=appuser:appuser requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

COPY --chown=appuser:appuser main.py .

EXPOSE 8080

# Healthcheck para local
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8080/health', timeout=3).status == 200 else 1)" || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
