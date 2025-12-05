"""Custom middleware for request processing."""

import time
import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging requests and timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process and log the request."""
        start_time = time.perf_counter()

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.perf_counter() - start_time

        # Add timing header
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        # Log request (skip health checks to reduce noise)
        if not request.url.path.endswith("/health"):
            logger.info(
                f"{request.method} {request.url.path} - {response.status_code} ({process_time:.4f}s)"
            )

        return response
