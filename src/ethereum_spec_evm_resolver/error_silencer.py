"""
This module provides a function to suppress specific benign errors that can appear
during normal operation of HTTP servers, particularly when using Python's built-in
HTTP server implementation with Unix sockets.
"""
import socketserver
import sys
from http.server import BaseHTTPRequestHandler

def apply_benign_error_silencer():
    """
    Silence specific benign errors in HTTP servers that would otherwise clutter logs.
    
    1. "I/O operation on closed file" errors:
       These occur when clients disconnect before the server finishes writing the response.
       This is normal HTTP connection behavior and not indicative of actual problems.

    2. "Unsupported method ('GET')" errors:
       These occur when a server receives GET requests (often heartbeat checks) but
       doesn't have a `do_GET` method implemented. Since these requests are usually just
       connection checks and don't affect server functionality, we can safely silence them.
    """

    # 1) Silence "I/O operation on closed file" errors
    original_handle_error = socketserver.BaseServer.handle_error
    def custom_handle_error(self, request, client_address):
        _, exc_value, _ = sys.exc_info()
        if exc_value is not None:
            error_message = str(exc_value)
            if ("I/O operation on closed file" in error_message):
                return
        original_handle_error(self, request, client_address)
    socketserver.BaseServer.handle_error = custom_handle_error

    # 2) Silence "Unsupported method ('GET')" errors 
    original_log_error = getattr(BaseHTTPRequestHandler, 'log_error', None)
    if original_log_error is not None:
        def custom_log_error(self, format, *args):
            message = format % args if args else format
            if "code 501, message Unsupported method ('GET')" in message:
                return
            original_log_error(self, format, *args)
        BaseHTTPRequestHandler.log_error = custom_log_error