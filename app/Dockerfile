FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# The image tag (sha-xxxxxxx) is baked in by CI so the running pod can report its version.
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

# Numeric, non-root user: lets Kubernetes enforce runAsNonRoot without resolving a user name.
USER 10001:10001

EXPOSE 8000

# In Kubernetes the Deployment overrides this command to restrict --forwarded-allow-ips.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
