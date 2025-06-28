from fastapi import Request, Response
from logger import log_request
from typing import Callable

async def log_requests_middleware(request: Request, call_next: Callable[..., Response]) -> Response:
    try:
        user = request.state.user.get("username", "-")
    except:
        user = "-"

    method = request.method
    endpoint = request.url.path

    response = await call_next(request)

    log_request(
        user=user,
        method=method,
        endpoint=endpoint,
        status=response.status_code
    )

    return response