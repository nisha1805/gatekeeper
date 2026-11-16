# Compliance service. Build context: app/compliance
# The base image is pinned by tag only for now; pinning by digest is a planned step.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv/compliance

COPY requirements-runtime.txt .
RUN pip install --no-cache-dir -r requirements-runtime.txt

COPY . .
# Files copied from a folder with owner-only permissions would be unreadable for the non-root user.
RUN chmod -R a+rX /srv/compliance

# Numeric non-root user, so Kubernetes (and the Kyverno policy) can verify it.
USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
