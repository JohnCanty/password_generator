"""Gunicorn configuration for internet-facing password generator deployments.

The default bind target is localhost so a reverse proxy can terminate TLS,
apply network policy, and expose the service safely. If you intentionally bind
Gunicorn to a public interface, configure TLS_CERTFILE and TLS_KEYFILE or set
ALLOW_INSECURE_PUBLIC_BIND=true after accepting that risk.
"""

from __future__ import annotations

import os
from pathlib import Path


def env_flag(name: str, default: bool = False) -> bool:
    """Read a boolean flag from the environment."""
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def bind_is_public(value: str) -> bool:
    """Return True when Gunicorn is configured to listen on all interfaces."""
    normalized = value.strip().lower()
    return normalized.startswith("0.0.0.0:") or normalized.startswith("[::]:")


# Server socket
bind = os.getenv("GUNICORN_BIND", "127.0.0.1:2048")
backlog = int(os.getenv("GUNICORN_BACKLOG", "2048"))

# TLS is optional when a reverse proxy terminates HTTPS, but required for a
# direct public bind unless ALLOW_INSECURE_PUBLIC_BIND is explicitly enabled.
certfile = os.getenv("TLS_CERTFILE") or None
keyfile = os.getenv("TLS_KEYFILE") or None
do_handshake_on_connect = bool(certfile and keyfile)

# Worker processes
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
worker_class = "sync"
worker_connections = int(os.getenv("GUNICORN_WORKER_CONNECTIONS", "1000"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "2"))

# Request limits
limit_request_line = 4094
limit_request_fields = 50
limit_request_field_size = 8190

# Server mechanics
daemon = False
pidfile = None
umask = 0o027
user = os.getenv("GUNICORN_USER") or None
group = os.getenv("GUNICORN_GROUP") or None
tmp_upload_dir = None
forwarded_allow_ips = os.getenv("FORWARDED_ALLOW_IPS", "127.0.0.1,::1")

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "password_generator"


def validate_tls_files() -> None:
    """Ensure TLS settings are complete and point to readable files."""
    if bool(certfile) != bool(keyfile):
        raise RuntimeError(
            "TLS_CERTFILE and TLS_KEYFILE must be set together when enabling TLS."
        )

    for path in [certfile, keyfile]:
        if path and not Path(path).is_file():
            raise RuntimeError(f"Configured TLS file does not exist: {path}")


def on_starting(server):
    """Validate security-sensitive settings before the master process starts."""
    validate_tls_files()

    if bind_is_public(bind) and not (certfile and keyfile) and not env_flag(
        "ALLOW_INSECURE_PUBLIC_BIND",
        default=False,
    ):
        raise RuntimeError(
            "Refusing to bind Gunicorn publicly without TLS. Keep the default "
            "localhost bind behind a reverse proxy, or set TLS_CERTFILE and "
            "TLS_KEYFILE."
        )

    server.log.info("Starting Password Generator on %s", bind)


def on_reload(server):
    """Log configuration reloads for operator visibility."""
    server.log.info("Reloading Password Generator")


def when_ready(server):
    """Log readiness once Gunicorn has finished starting workers."""
    server.log.info("Password Generator is ready to accept connections")


def on_exit(server):
    """Log shutdown events to simplify operational troubleshooting."""
    server.log.info("Shutting down Password Generator")
