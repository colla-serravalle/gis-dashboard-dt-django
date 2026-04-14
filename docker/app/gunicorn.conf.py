bind = "0.0.0.0:8000"
worker_tmp_dir = "/tmp"
workers = 3
worker_class = "gthread"
threads = 4
timeout = 120
max_requests = 1000
max_requests_jitter = 50
accesslog = "-"   # stdout → docker compose logs
errorlog = "-"    # stderr → docker compose logs
loglevel = "info"

# Prevent oversized requests
limit_request_line = 4094
limit_request_fields = 50
limit_request_field_size = 8190
