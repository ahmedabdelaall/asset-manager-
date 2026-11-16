# Asset Master - container image
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AM_INSTANCE=/data \
    AM_HOST=0.0.0.0 \
    AM_PORT=5222

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY VERSION CHANGELOG.md ./
COPY core ./core
COPY tools ./tools

# Run as an unprivileged user; all company data lives in the /data volume
RUN useradd --create-home --uid 10001 appuser && mkdir -p /data && chown -R appuser /data /app
USER appuser
VOLUME ["/data"]
EXPOSE 5222

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import os,urllib.request;urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('AM_PORT','5222'), timeout=4)" || exit 1

CMD ["python", "-m", "core"]
