import sys
from datetime import datetime


def request_log_middleware(get_response):
    """Log each request to stderr so the terminal shows method, path, and status."""

    def middleware(request):
        response = get_response(request)
        try:
            ts = datetime.now().strftime("%d/%b/%Y %H:%M:%S")
            line = f'[{ts}] "{request.method} {request.path} HTTP/1.1" {response.status_code}\n'
            sys.stderr.write(line)
            sys.stderr.flush()
        except Exception:
            pass
        return response

    return middleware
