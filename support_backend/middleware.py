from fastapi import Request, Response
from typing import Callable
import json
import time
from logger import log_request, mask_sensitive_data
from logging import getLogger

logger = getLogger("app")


async def log_requests_middleware(request: Request, call_next: Callable) -> Response:
    start_time = time.time()

    # === Захват тела запроса ===
    request_body = None
    try:
        # Читаем тело запроса только если это не GET/HEAD и есть content-length
        if request.method not in ("GET", "HEAD") and request.headers.get("content-length"):
            body = await request.body()
            # Сохраняем для повторного использования
            request._body = body

            # Парсим JSON если возможно
            try:
                decoded = body.decode("utf-8")
                if decoded.strip():
                    try:
                        request_body = json.loads(decoded)
                    except json.JSONDecodeError:
                        request_body = decoded
            except Exception:
                request_body = "<binary_data>"
        else:
            request_body = None
    except Exception as e:
        request_body = f"<error_reading_body: {str(e)}>"

    # === Определение пользователя ===
    user = "anonymous"
    client_ip = request.client.host if request.client else "-"

    # === Обработка запроса ===
    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception("Unhandled exception in request flow")
        response = Response(
            content=json.dumps({"detail": "Internal Server Error"}),
            status_code=500,
            media_type="application/json"
        )

    # === Захват тела ответа ===
    response_body = None
    try:
        # Для JSON ответов
        if hasattr(response, "body") and response.body:
            try:
                decoded = response.body.decode("utf-8")
                if decoded.strip():
                    try:
                        response_body = json.loads(decoded)
                    except json.JSONDecodeError:
                        response_body = decoded
            except Exception:
                response_body = "<binary_response>"
    except Exception as e:
        response_body = f"<error_reading_response: {str(e)}>"

    process_time = time.time() - start_time

    # === Маскировка чувствительных данных ===
    safe_request_body = mask_sensitive_data(request_body)
    safe_response_body = mask_sensitive_data(response_body)

    # === Логирование ===
    method = request.method
    endpoint = request.url.path
    status_code = response.status_code

    # Пытаемся получить пользователя из request.state (если установлено в get_current_user)
    try:
        if hasattr(request.state, "user"):
            user = request.state.user.get("username", "authenticated")
        elif request.headers.get("authorization"):
            user = "authenticated"
    except Exception:
        user = "anonymous"

    details = f"client_ip: {client_ip}, process_time: {process_time:.3f}s"

    log_request(
        user=user,
        method=method,
        endpoint=endpoint,
        status=status_code,
        details=details,
        request_body=safe_request_body,
        response_body=safe_response_body,
    )

    return response