# OmniPitch — FastAPI backend + dashboard, ready for Azure Container Apps
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY foundry ./foundry
# Editable install keeps the dashboard assets and agent manifest next to the code
RUN pip install -e ".[azure]" && useradd --create-home omnipitch
USER omnipitch

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["uvicorn", "omnipitch.api:app", "--host", "0.0.0.0", "--port", "8000"]
