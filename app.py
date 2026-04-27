"""Flask application for a dual-mode password generator.

The web interface supports two generation modes:
- Server-side generation through the ``/api/generate`` endpoint.
- Local generation in the browser using the Web Crypto API.

The API remains available for operators who prefer server-side entropy sources,
but the application now defaults to a hardened deployment model that is safer
for internet-facing use behind a reverse proxy.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import secrets
import string
from typing import Any
from urllib.parse import urlparse

from flask import Flask, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import BadRequest
from werkzeug.middleware.proxy_fix import ProxyFix


def env_flag(name: str, default: bool = False) -> bool:
    """Read a boolean flag from the environment."""
    value = os.getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


app = Flask(__name__)
app.config.update(
    MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH_BYTES", "4096")),
    RATELIMIT_HEADERS_ENABLED=True,
)

if env_flag("TRUST_PROXY_HEADERS"):
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, logging.INFO)
logging.basicConfig(level=log_level)
app.logger.setLevel(log_level)

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
)

# Password generation defaults shared by the server and documented for the UI.
DEFAULT_PASSWORD_LENGTH = 8
MIN_PASSWORD_LENGTH = 4
MAX_PASSWORD_LENGTH = 128
DEFAULT_SPECIAL_CHARS = "!@#*"
MAX_SPECIAL_CHARS_INPUT = 128
LOCAL_GENERATION_DEFAULT = env_flag("LOCAL_GENERATION_DEFAULT", default=False)

# Character pools used for secure password generation and strength checks.
UPPERCASE = string.ascii_uppercase
LOWERCASE = string.ascii_lowercase
DIGITS = string.digits
PUNCTUATION = string.punctuation
AMBIGUOUS_CHARS = "0Ol1I"


def sanitize_length(length_value: Any) -> int:
    """Normalize user-supplied length to the supported password range."""
    try:
        length = int(length_value)
    except (TypeError, ValueError):
        return DEFAULT_PASSWORD_LENGTH

    return max(MIN_PASSWORD_LENGTH, min(length, MAX_PASSWORD_LENGTH))


def sanitize_special_chars(special_chars_value: Any) -> str:
    """Return a bounded ASCII punctuation whitelist for password generation."""
    if not isinstance(special_chars_value, str):
        return DEFAULT_SPECIAL_CHARS

    raw_value = special_chars_value.strip()
    if not raw_value or len(raw_value) > MAX_SPECIAL_CHARS_INPUT:
        return DEFAULT_SPECIAL_CHARS

    chars = "".join(part.strip() for part in raw_value.split(","))
    filtered_chars = []
    seen_chars = set()
    for char in chars:
        if char in PUNCTUATION and char not in seen_chars:
            filtered_chars.append(char)
            seen_chars.add(char)

    return "".join(filtered_chars) or DEFAULT_SPECIAL_CHARS


def sanitize_boolean(value: Any, default: bool = True) -> bool:
    """Convert JSON-style truthy values into a predictable Python boolean."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}

    return bool(value)


def calculate_password_strength(password: str, length: int) -> str:
    """Estimate password strength using length and character diversity."""
    has_upper = any(char in UPPERCASE for char in password)
    has_lower = any(char in LOWERCASE for char in password)
    has_digit = any(char in DIGITS for char in password)
    has_special = any(char in PUNCTUATION for char in password)
    diversity = sum([has_upper, has_lower, has_digit, has_special])

    if length >= 12 and diversity >= 3:
        return "strong"
    if length >= 10 and diversity >= 2:
        return "medium"
    if length >= 8 and diversity >= 2:
        return "medium"
    return "weak"


def build_character_pool(special_chars: str, exclude_ambiguous: bool) -> str:
    """Build the allowed character pool for password generation."""
    char_pool = UPPERCASE + LOWERCASE + DIGITS + special_chars

    if exclude_ambiguous:
        char_pool = "".join(char for char in char_pool if char not in AMBIGUOUS_CHARS)

    return char_pool or (LOWERCASE + DIGITS)


def generate_password(
    length: int, special_chars: str, exclude_ambiguous: bool
) -> tuple[str, str]:
    """Generate a cryptographically secure password and return its strength."""
    char_pool = build_character_pool(special_chars, exclude_ambiguous)
    password = "".join(secrets.choice(char_pool) for _ in range(length))
    strength = calculate_password_strength(password, length)
    return password, strength


def create_json_error(message: str, status_code: int):
    """Return a standard JSON error payload for API and health responses."""
    response = jsonify({"success": False, "error": message})
    response.status_code = status_code
    return response


def request_origin_is_trusted() -> bool:
    """Allow same-origin browser requests while still permitting non-browser clients."""
    origin = request.headers.get("Origin")
    if not origin:
        return True

    origin_parts = urlparse(origin)
    request_parts = urlparse(request.host_url)
    return origin_parts.netloc == request_parts.netloc


def client_is_local() -> bool:
    """Return True when the request originates from the local machine."""
    remote_addr = request.remote_addr
    if not remote_addr:
        return False

    try:
        return ipaddress.ip_address(remote_addr).is_loopback
    except ValueError:
        return False


@app.after_request
def set_security_headers(response):
    """Apply browser hardening headers and secret-safe caching directives."""
    response.headers.setdefault(
        "Content-Security-Policy",
        "; ".join(
            [
                "default-src 'self'",
                "script-src 'self'",
                "style-src 'self'",
                "img-src 'self' data:",
                "connect-src 'self'",
                "font-src 'self'",
                "base-uri 'self'",
                "form-action 'self'",
                "frame-ancestors 'none'",
                "object-src 'none'",
            ]
        ),
    )
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
    response.headers.setdefault(
        "Permissions-Policy",
        "accelerometer=(), camera=(), geolocation=(), gyroscope=(), magnetometer=(), microphone=(), payment=(), usb=()",
    )
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")

    if request.is_secure:
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )

    if request.endpoint in {"index", "api_generate_password"} or request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

    return response


@app.errorhandler(413)
def request_entity_too_large(_error):
    """Return a consistent error when a request body exceeds the configured cap."""
    return create_json_error("Request body too large.", 413)


@app.errorhandler(429)
def rate_limit_exceeded(error):
    """Return a JSON error when a client exceeds the API rate limit."""
    message = getattr(error, "description", "Rate limit exceeded.")
    return create_json_error(message, 429)


@app.route("/")
def index():
    """Render the main page and expose UI defaults to the template."""
    return render_template(
        "index.html",
        default_length=DEFAULT_PASSWORD_LENGTH,
        min_length=MIN_PASSWORD_LENGTH,
        max_length=MAX_PASSWORD_LENGTH,
        default_special_chars_display=", ".join(DEFAULT_SPECIAL_CHARS),
        max_special_chars_input=MAX_SPECIAL_CHARS_INPUT,
        local_generation_default=LOCAL_GENERATION_DEFAULT,
    )


@app.route("/api/generate", methods=["POST"])
@limiter.limit(os.getenv("GENERATE_RATE_LIMIT", "30 per minute"))
def api_generate_password():
    """Generate a password on the server after validating the request body."""
    if not request_origin_is_trusted():
        app.logger.warning(
            "Rejected cross-origin password generation request from %s with origin %s",
            request.remote_addr,
            request.headers.get("Origin"),
        )
        return create_json_error("Cross-origin requests are not allowed.", 403)

    if not request.is_json:
        app.logger.warning(
            "Rejected non-JSON password generation request from %s",
            request.remote_addr,
        )
        return create_json_error("Expected a JSON request body.", 400)

    try:
        data = request.get_json(silent=False)
    except BadRequest:
        app.logger.warning(
            "Rejected malformed JSON password generation request from %s",
            request.remote_addr,
        )
        return create_json_error("Malformed JSON request.", 400)

    if not isinstance(data, dict):
        app.logger.warning(
            "Rejected non-object JSON password generation request from %s",
            request.remote_addr,
        )
        return create_json_error("JSON payload must be an object.", 400)

    length = sanitize_length(data.get("length", DEFAULT_PASSWORD_LENGTH))
    special_chars = sanitize_special_chars(
        data.get("special_chars", DEFAULT_SPECIAL_CHARS)
    )
    exclude_ambiguous = sanitize_boolean(
        data.get("exclude_ambiguous"),
        default=True,
    )

    try:
        password, strength = generate_password(length, special_chars, exclude_ambiguous)
    except Exception:
        app.logger.exception(
            "Unexpected error during server-side password generation for %s",
            request.remote_addr,
        )
        return create_json_error("Password generation failed.", 500)

    return jsonify(
        {
            "success": True,
            "password": password,
            "strength": strength,
            "length": length,
            "mode": "server",
        }
    )


@app.route("/health")
def health():
    """Expose a minimal health check, restricted to localhost by default."""
    if not env_flag("ALLOW_REMOTE_HEALTHCHECKS", default=False) and not client_is_local():
        app.logger.warning(
            "Rejected remote health check from %s",
            request.remote_addr,
        )
        return create_json_error("Health checks are only available from localhost.", 403)

    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    # The development server binds to localhost by default. Use Gunicorn behind
    # a reverse proxy for production deployments.
    app.run(
        debug=False,
        host=os.getenv("FLASK_RUN_HOST", "127.0.0.1"),
        port=int(os.getenv("FLASK_RUN_PORT", "2048")),
    )
