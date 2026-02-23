# Secure Password Generator

A Flask-based web application for generating cryptographically secure passwords using Python's `secrets` module. Designed to run on Raspberry Pi with TruRNG hardware entropy source for maximum security.

## Features

- **Cryptographically Secure**: Uses Python's `secrets` module for secure random number generation
- **Customizable Length**: Generate passwords from 4 to 128 characters
- **Quick Select**: Pre-configured buttons for common password lengths (8, 10, 12, 16)
- **Custom Special Characters**: Define your own set of special characters (comma-separated)
- **Exclude Ambiguous Characters**: Option to exclude easily confused characters (0, O, l, 1, I)
- **Password Strength Indicator**: Visual feedback on password strength (weak/medium/strong)
- **Copy to Clipboard**: One-click copying with visual feedback
- **Input Sanitization**: All user inputs are properly sanitized for security
- **Clean UI**: Modern, responsive interface that works on all devices
- **No Data Storage**: Passwords are never stored or transmitted (client-side only)

## Requirements

- Python 3.7 or higher
- pip (Python package installer)
- virtualenv (recommended)

## Installation

### Step 1: Navigate to Project Directory

```bash
cd /home/user/password_generator
```

### Step 2: Create Python Virtual Environment

```bash
python3 -m venv venv
```

This creates an isolated Python environment in the `venv` directory.

### Step 3: Activate Virtual Environment

```bash
source venv/bin/activate
```

You should see `(venv)` appear in your terminal prompt, indicating the virtual environment is active.

### Step 4: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs Flask, Gunicorn, and all required dependencies.

## Running the Application

### Option 1: Using Gunicorn (Recommended for Production)

```bash
gunicorn -c gunicorn_config.py app:app
```

This starts the application on port 2048 using the Gunicorn WSGI server.

### Option 2: Running Gunicorn in Background

To run the application as a background process:

```bash
gunicorn -c gunicorn_config.py app:app &
```

To stop the background process later:

```bash
# Find the process ID
ps aux | grep gunicorn

# Kill the process (replace PID with actual process ID)
kill <PID>
```

### Option 3: Using Flask Development Server (Testing Only)

For development/testing purposes only:

```bash
python app.py
```

**Warning**: The Flask development server is not suitable for production use.

## Accessing the Application

Once the application is running, open your web browser and navigate to:

```
http://localhost:2048
```

Or if accessing from another device on your network:

```
http://<raspberry-pi-ip>:2048
```

Replace `<raspberry-pi-ip>` with your Raspberry Pi's IP address (find it using `hostname -I`).

## Using the Password Generator

1. **Set Password Length**: Enter a custom length (4-128) or click a quick-select button (8, 10, 12, 16)
2. **Customize Special Characters**: Enter comma-separated special characters (default: !, @, #, *)
3. **Exclude Ambiguous**: Keep checkbox checked to avoid confusing characters (0, O, l, 1, I)
4. **Generate**: Click "Generate Password" button
5. **Copy**: Click the "Copy" button to copy password to clipboard
6. **Strength Indicator**: View password strength (weak/medium/strong)

## Configuration

### Changing Port

To run on a different port, edit `gunicorn_config.py`:

```python
bind = "0.0.0.0:YOUR_PORT"
```

Or specify it directly in the command:

```bash
gunicorn -b 0.0.0.0:YOUR_PORT app:app
```

### Worker Configuration

Adjust the number of worker processes in `gunicorn_config.py`:

```python
workers = 2  # Change based on your CPU cores
```

Recommended: 2-4 workers for Raspberry Pi 4, 1-2 for older models.

## Security Features

- **Cryptographic Random Generation**: Uses `secrets.choice()` for cryptographically strong randomness
- **Input Sanitization**: All user inputs are validated and sanitized
- **No Password Storage**: Passwords are generated client-side and never stored
- **XSS Protection**: HTML escaping prevents cross-site scripting
- **CORS Protection**: Flask's default CORS policy prevents unauthorized access

## Troubleshooting

### Port Already in Use

If port 2048 is already in use:

```bash
# Find process using port 2048
sudo lsof -i :2048

# Kill the process
sudo kill -9 <PID>
```

### Permission Denied on Port

If you get permission errors, either:
- Use a port above 1024 (like 2048 - already configured)
- Or run with sudo (not recommended): `sudo gunicorn -c gunicorn_config.py app:app`

### Virtual Environment Issues

If you have issues with the virtual environment:

```bash
# Deactivate current environment
deactivate

# Remove old environment
rm -rf venv

# Create fresh environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Starting on Boot (Optional)

To automatically start the application on system boot, create a systemd service:

1. Create service file:

```bash
sudo nano /etc/systemd/system/password-generator.service
```

2. Add the following content (adjust paths as needed):

```ini
[Unit]
Description=Password Generator Web Application
After=network.target

[Service]
Type=notify
User=user
WorkingDirectory=/home/user/password_generator
Environment="PATH=/home/user/password_generator/venv/bin"
ExecStart=/home/user/password_generator/venv/bin/gunicorn -c gunicorn_config.py app:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
KillSignal=SIGTERM
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable password-generator
sudo systemctl start password-generator
```

4. Check status:

```bash
sudo systemctl status password-generator
```

## API Documentation

### Generate Password Endpoint

**URL**: `/api/generate`  
**Method**: `POST`  
**Content-Type**: `application/json`

**Request Body**:
```json
{
    "length": 12,
    "special_chars": "!,@,#,$,%,&,*",
    "exclude_ambiguous": true
}
```

**Response**:
```json
{
    "success": true,
    "password": "password is here",
    "strength": "strong",
    "length": 12
}
```

### Health Check Endpoint

**URL**: `/health`  
**Method**: `GET`

**Response**:
```json
{
    "status": "healthy"
}
```

## Contributing

This is a standalone application. Feel free to modify and customize it for your needs.

## License

This project is open source "The Unlicense"

## Acknowledgments

- Built with Flask and Gunicorn
- Designed for Raspberry Pi with TruRNG hardware entropy source
- Uses Python's `secrets` module for cryptographic security

## Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Verify all dependencies are installed: `pip list`
3. Check Gunicorn logs for errors
4. Ensure port 2048 is not blocked by firewall

---

**Note**: This application runs on localhost (127.0.0.1) of the Raspberry Pi. To access it from other devices on your network, use the Raspberry Pi's IP address instead of localhost.

## Quick Start

```bash
# 1. Navigate to directory
cd /home/user/password_generator

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate virtual environment
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run application
gunicorn -c gunicorn_config.py app:app

# 6. Open browser
# Visit: http://localhost:2048
```
