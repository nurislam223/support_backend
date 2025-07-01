from fastapi import Request, Response, HTTPException
from typing import Callable
import json
from logger import log_request
from auth import get_current_user

async def log_requests_middleware(request: Request, call_next: Callable[..., Response]) -> Response:
    # Получаем пользователя из request.state
    try:
        user = request.state.user.get("username", "-")
    except:
        user = "-"

    method = request.method
    endpoint = request.url.path

    response = await call_next(request)

    # Пытаемся получить тело ответа, если доступно
    details = ""
    if hasattr(response, "body"):
        try:
            body = getattr(response, "body", b"")
            decoded_body = body.decode("utf-8") if body else ""
            details = f"Response Body: {decoded_body}"
        except Exception as e:
            details = f"<failed to decode body: {str(e)}>"

    # Логируем
    log_request(
        user=user,
        method=method,
        endpoint=endpoint,
        status=response.status_code,
        details=details
    )

    return response

