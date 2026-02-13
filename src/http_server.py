"""
HTTP Server for receiving Claude Code hook events.
Listens on localhost:27182 for JSON POST requests.
"""

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ClaudeCodeHTTPHandler(BaseHTTPRequestHandler):
    """Handler for Claude Code hook events."""

    # Class variables to store callbacks
    event_callback: Optional[Callable] = None
    status_callback: Optional[Callable] = None

    def log_message(self, format, *args):
        """Override to use Python logging instead of stderr."""
        logger.debug(f"{self.address_string()} - {format % args}")

    def do_POST(self):
        """Handle POST requests from Claude Code hooks."""
        try:
            # Parse path
            path = self.path

            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'

            # Parse JSON
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {body[:200]}")
                self.send_response(400)
                self.end_headers()
                return

            # Route based on path
            if path == '/hook':
                self._handle_hook(data)
            elif path == '/pin':
                self._handle_pin(data)
            elif path == '/unpin':
                self._handle_unpin(data)
            elif path == '/health':
                self._handle_health()
            elif path == '/status':
                self._send_status_response()
                return
            else:
                self.send_response(404)
                self.end_headers()
                return

            # Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({"status": "ok"})
            self.wfile.write(response.encode('utf-8'))

        except Exception as e:
            logger.error(f"Error handling POST request: {e}", exc_info=True)
            self.send_response(500)
            self.end_headers()

    def do_GET(self):
        """Handle GET requests (health check, status)."""
        if self.path == '/health':
            self._handle_health()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            response = json.dumps({"status": "running"})
            self.wfile.write(response.encode('utf-8'))
        elif self.path == '/status':
            self._send_status_response()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_hook(self, data: dict):
        """Handle hook event."""
        if self.event_callback:
            self.event_callback('hook', data)
        logger.debug(f"Hook event: {data.get('eventType', 'unknown')}")

    def _handle_pin(self, data: dict):
        """Handle pin session event."""
        if self.event_callback:
            self.event_callback('pin', data)
        logger.info(f"Pin session: {data.get('sessionId', 'unknown')}")

    def _handle_unpin(self, data: dict):
        """Handle unpin session event."""
        if self.event_callback:
            self.event_callback('unpin', data)
        logger.info("Unpin all sessions")

    def _handle_health(self):
        """Handle health check."""
        logger.debug("Health check")

    def _handle_status(self):
        """Handle status request."""
        logger.debug("Status request")

    def _send_status_response(self):
        """Send status response with real session data."""
        if self.status_callback:
            try:
                status_data = self.status_callback()
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                status_data = {"status": "error", "error": str(e)}
        else:
            status_data = {"status": "running"}
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status_data).encode('utf-8'))


class ClaudeCodeServer:
    """HTTP server for Claude Code integration."""

    def __init__(self, port: int = 27182, event_callback: Optional[Callable] = None,
                 status_callback: Optional[Callable] = None):
        """
        Initialize server.

        Args:
            port: Port to listen on (default: 27182)
            event_callback: Callback function(event_type: str, data: dict)
            status_callback: Callback function() -> dict for /status endpoint
        """
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[Thread] = None
        self.running = False

        # Set callbacks on handler class
        ClaudeCodeHTTPHandler.event_callback = event_callback
        ClaudeCodeHTTPHandler.status_callback = status_callback

    def start(self):
        """Start the HTTP server in a background thread."""
        if self.running:
            logger.warning("Server already running")
            return

        try:
            self.server = HTTPServer(('localhost', self.port), ClaudeCodeHTTPHandler)
            self.running = True

            # Start server in background thread
            self.thread = Thread(target=self._run_server, daemon=True)
            self.thread.start()

            logger.info(f"Claude Code server started on http://localhost:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise

    def _run_server(self):
        """Run the server (called in background thread)."""
        try:
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            self.running = False

    def stop(self):
        """Stop the HTTP server."""
        if not self.running:
            return

        logger.info("Stopping server...")
        self.running = False

        if self.server:
            self.server.shutdown()
            self.server.server_close()

        if self.thread:
            self.thread.join(timeout=2.0)

        logger.info("Server stopped")

    def is_running(self) -> bool:
        """Check if server is running."""
        return self.running


if __name__ == "__main__":
    # Test server
    logging.basicConfig(level=logging.DEBUG)

    def test_callback(event_type: str, data: dict):
        print(f"Event: {event_type}, Data: {json.dumps(data, indent=2)}")

    server = ClaudeCodeServer(event_callback=test_callback)
    server.start()

    try:
        print("Server running. Press Ctrl+C to stop...")
        while server.is_running():
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        server.stop()
