# Secure Password Generator

A Flask-based password generator with two generation modes:

- Server mode is the default. The browser sends generation options to the Flask API, and the server returns the generated password.
- Local mode is optional. The browser uses the Web Crypto API so the generated password never leaves the browser.

The project is designed for small self-hosted deployments, but it now includes the basic controls expected for an internet-facing service: rate limiting, request-size limits, restrictive security headers, no-store cache headers for secret-bearing responses, and safer Gunicorn defaults.

## Security Model

- Server mode transmits the generated password from the server to the browser. Use HTTPS end to end and assume the password is visible to the application server and any TLS terminator or proxy that handles the response.
- Local mode keeps password generation in the browser and avoids transmitting the generated password to the server.
- The application does not intentionally persist generated passwords to disk or a database.
- The `/api/generate` endpoint is rate limited and only accepts JSON requests.
- The `/health` endpoint is restricted to localhost by default.
- Gunicorn binds to `127.0.0.1:2048` by default so a reverse proxy can handle public TLS and network controls.

## Project Layout

- `app.py`: Flask routes, input validation, security headers, rate limiting, and server-side password generation.
- `gunicorn_config.py`: Hardened Gunicorn defaults and startup validation for public binds and TLS settings.
- `templates/index.html`: Main UI, including the local-generation toggle.
- `static/script.js`: Browser behavior, local Web Crypto generation, API calls, strength display, and clipboard support.
- `static/style.css`: Application styling.
- `requirements.txt`: Python package dependencies.

## Features

- Cryptographically secure password generation using Python `secrets` in server mode.
- Cryptographically secure password generation using the Web Crypto API in local mode.
- Password lengths from 4 to 128 characters.
- Configurable punctuation characters.
- Optional exclusion of ambiguous characters: `0`, `O`, `l`, `1`, `I`.
- Visual password-strength indicator.
- Copy-to-clipboard support.
- JSON API for server-side generation.
- Security headers and no-store cache headers on the main page and API responses.

## Requirements

- Python 3.9 or newer.
- `pip`.
- A virtual environment is strongly recommended.
- A reverse proxy such as Nginx, Caddy, or a cloud load balancer for public deployments.

## Installation

```bash
cd /home/user/password_generator
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running The Application

### Development

The built-in Flask server now binds to localhost by default:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:2048
```

### Production With Gunicorn

Gunicorn also binds to localhost by default so that a reverse proxy can publish the service securely:

```bash
gunicorn -c gunicorn_config.py app:app
```

By default, this listens on:

```text
127.0.0.1:2048
```

### Production With Caddy

The repository now includes a production-oriented [Caddyfile](Caddyfile) for automatic HTTPS and reverse proxying to Gunicorn on localhost.

Before using it:

- Replace `admin@example.com` with your ACME contact email.
- Replace `passwords.example.com` with the real public hostname for the service.
- Keep Gunicorn bound to `127.0.0.1:2048`.
- Run the Flask app with `TRUST_PROXY_HEADERS=true` so Flask interprets forwarded scheme and host values correctly.

On Debian 13, a typical flow is:

```bash
sudo apt update
sudo apt install -y caddy
sudo cp /path/to/password_generator/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

If you manage Gunicorn with `systemd`, add `Environment=TRUST_PROXY_HEADERS=true` to the service unit.

## Configuration

The application is configured through environment variables.

- `FLASK_RUN_HOST`: Override the Flask development server bind address. Default: `127.0.0.1`.
- `FLASK_RUN_PORT`: Override the Flask development server port. Default: `2048`.
- `LOCAL_GENERATION_DEFAULT`: Set to `true` to default the UI to browser-side generation.
- `MAX_CONTENT_LENGTH_BYTES`: Maximum request size accepted by Flask. Default: `4096`.
- `GENERATE_RATE_LIMIT`: Rate limit applied to `POST /api/generate`. Default: `30 per minute`.
- `RATELIMIT_STORAGE_URI`: Storage backend for Flask-Limiter. Default: `memory://`.
- `TRUST_PROXY_HEADERS`: Set to `true` when running behind a reverse proxy that sets forwarded headers.
- `ALLOW_REMOTE_HEALTHCHECKS`: Set to `true` if a remote monitor must access `/health`.

Gunicorn-specific settings:

- `GUNICORN_BIND`: Gunicorn bind target. Default: `127.0.0.1:2048`.
- `GUNICORN_WORKERS`: Worker count. Default: `2`.
- `GUNICORN_TIMEOUT`: Worker timeout in seconds. Default: `30`.
- `GUNICORN_KEEPALIVE`: Keepalive timeout in seconds. Default: `2`.
- `TLS_CERTFILE`: PEM certificate file when Gunicorn terminates TLS directly.
- `TLS_KEYFILE`: PEM private key file when Gunicorn terminates TLS directly.
- `ALLOW_INSECURE_PUBLIC_BIND`: Set to `true` only if you intentionally bind Gunicorn publicly without TLS and accept that risk.
- `FORWARDED_ALLOW_IPS`: Proxy IP allowlist for forwarded headers. Default: `127.0.0.1,::1`.

## Reverse Proxy Guidance

For public deployments, run Gunicorn behind a reverse proxy. The proxy should:

- Terminate HTTPS.
- Redirect HTTP to HTTPS.
- Restrict request sizes.
- Apply connection or request-rate controls.
- Forward `X-Forwarded-For` and `X-Forwarded-Proto` only from trusted sources.

The included [Caddyfile](Caddyfile) does the following:

- Terminates HTTPS automatically.
- Compresses responses with `zstd` and `gzip`.
- Caps request bodies at `4KB` to match the Flask-side request size limit.
- Proxies traffic to Gunicorn on `127.0.0.1:2048`.
- Performs active health checks against `/health`.
- Writes JSON access logs to `/var/log/caddy/password-generator-access.log`.

Example Caddy configuration:

```caddyfile
{
  email admin@example.com
}

passwords.example.com {
  encode zstd gzip

  request_body {
    max_size 4KB
  }

  header {
    -Server
  }

  reverse_proxy 127.0.0.1:2048 {
    health_uri /health
    health_interval 30s
    health_timeout 5s
  }

  log {
    output file /var/log/caddy/password-generator-access.log {
      roll_size 10MiB
      roll_keep 10
      roll_keep_for 720h
    }
    format json
  }
}
```

Example Nginx site configuration:

```nginx
server {
    listen 443 ssl http2;
    server_name passwords.example.com;

    ssl_certificate /etc/letsencrypt/live/passwords.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/passwords.example.com/privkey.pem;

    client_max_body_size 4k;

    location / {
        proxy_pass http://127.0.0.1:2048;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
    }
}
```

If you enable `TRUST_PROXY_HEADERS=true`, make sure only your trusted reverse proxy can send forwarded headers.

## UI Behavior

The main page exposes a checkbox labeled `Generate locally in this browser`.

- Unchecked: server mode. The browser calls `POST /api/generate`.
- Checked: local mode. The browser generates the password with `window.crypto.getRandomValues`.

The default remains server mode unless `LOCAL_GENERATION_DEFAULT=true` is set.

## API Documentation

### `POST /api/generate`

Request body:

```json
{
  "length": 12,
  "special_chars": "!, @, #, $",
  "exclude_ambiguous": true
}
```

Notes:

- The request body must be JSON.
- `length` is clamped to the range `4..128`.
- `special_chars` accepts punctuation characters and ignores other input.
- Duplicate special characters are removed.

Successful response:

```json
{
  "success": true,
  "password": "example-password",
  "strength": "strong",
  "length": 12,
  "mode": "server"
}
```

Error response:

```json
{
  "success": false,
  "error": "Malformed JSON request."
}
```

### `GET /health`

Successful response:

```json
{
  "status": "healthy"
}
```

By default, this endpoint only answers localhost requests.

## Security Controls Implemented

- `Content-Security-Policy` restricts scripts, styles, and outbound connections to same-origin resources.
- `X-Frame-Options: DENY` blocks clickjacking via framing.
- `X-Content-Type-Options: nosniff` disables MIME sniffing.
- `Referrer-Policy: no-referrer` avoids leaking URLs via referrers.
- `Strict-Transport-Security` is sent on HTTPS responses.
- `Cache-Control: no-store` is sent for the main page and API responses.
- The API rejects malformed or non-JSON request bodies.
- The API enforces a per-client rate limit.
- Gunicorn refuses a public bind without TLS unless explicitly overridden.

## Operational Notes

- Local mode is the safer choice for users who do not need server-side generation.
- If you front the app with a reverse proxy, prefer binding Gunicorn to localhost and do not expose port `2048` publicly.
- The in-memory rate-limit backend is adequate for a single-process or single-host deployment. For multiple application instances, configure a shared backend such as Redis with `RATELIMIT_STORAGE_URI`.
- Review and update dependencies regularly.

## Troubleshooting

### `403 Cross-origin requests are not allowed`

The API saw an `Origin` header that did not match the current host. Make sure your reverse proxy forwards the correct host header and enable `TRUST_PROXY_HEADERS=true` when appropriate.

### `403 Health checks are only available from localhost`

Your monitoring system is reaching `/health` remotely. Either route the health check through a local reverse proxy or set `ALLOW_REMOTE_HEALTHCHECKS=true`.

### `429 Too Many Requests`

The client exceeded `GENERATE_RATE_LIMIT`. Increase the limit if your deployment requires it, but do not remove it for public deployments.

### Gunicorn refuses to start with a public bind

If `GUNICORN_BIND` is set to `0.0.0.0:2048` or another public bind, configure `TLS_CERTFILE` and `TLS_KEYFILE`, or switch back to the default localhost bind and place a reverse proxy in front.

## License

This project is released under The Unlicense. See `LICENSE` for details.
