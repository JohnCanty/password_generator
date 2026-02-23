"""
Gunicorn configuration file for Password Generator application
"""

# Server socket
bind = "0.0.0.0:2048"
backlog = 2048

# Worker processes
workers = 2
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "password_generator"

# Server hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    print("Starting Password Generator on port 2048...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    print("Reloading Password Generator...")

def when_ready(server):
    """Called just after the server is started."""
    print("Password Generator is ready to accept connections.")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    print("Shutting down Password Generator...")
