import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.utils.tracing import correlation_id_ctx, new_correlation_id


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("x-correlation-id", new_correlation_id())
        correlation_id_ctx.set(cid)
        request.state.correlation_id = cid

        started = time.perf_counter()
        response = await call_next(request)
        response.headers["x-correlation-id"] = cid
        response.headers["x-response-time-ms"] = str(int((time.perf_counter() - started) * 1000))
        return response
