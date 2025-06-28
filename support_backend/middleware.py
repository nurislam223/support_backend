from fastapi import Request, Response
from logger import log_request
from typing import Callable

async def log_requests_middleware(request: Request, call_next):
    # Получаем пользователя из request.state.user
    try:
        user = getattr(request.state, "user", {}).get("username", "-")
    except:
        user = "-"

    method = request.method
    endpoint = request.url.path

    # Выполняем запрос
    response = await call_next(request)

    # Логируем ответ
    log_request(
        user=user,
        method=method,
        endpoint=endpoint,
        status=response.status_code
    )

    return response