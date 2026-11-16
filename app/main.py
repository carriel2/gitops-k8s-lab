"""Demo API for the GitOps lab.

Small on purpose: the point of this repository is how the app is built, shipped and
operated on Kubernetes, not the app itself.
"""

import os
import socket

from fastapi import FastAPI, Request

app = FastAPI(title="gitops-k8s-lab demo API")

# Set at build time by the CI pipeline (see Dockerfile and .github/workflows/build.yml).
APP_VERSION = os.getenv("APP_VERSION", "dev")


@app.get("/health")
def health() -> dict:
    """Used by the readiness and liveness probes."""
    return {"status": "ok"}


@app.get("/")
def index() -> dict:
    return {
        "message": os.getenv("APP_GREETING", "Hello from the GitOps lab"),
        "version": APP_VERSION,
        "pod": socket.gethostname(),
        # True when the optional SealedSecret was decrypted and mounted as an env var.
        "secret_loaded": bool(os.getenv("APP_SECRET_TOKEN")),
    }


@app.get("/whoami")
def whoami(request: Request) -> dict:
    """Shows which client IP the app sees.

    Behind a WAF and a cloud load balancer the TCP peer is a cluster node, so the real
    client IP only exists in X-Forwarded-For. uvicorn trusts that header only when the
    connection comes from the CIDR passed in --forwarded-allow-ips (see the overlay).
    """
    return {
        "client_ip": request.client.host if request.client else None,
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
    }
