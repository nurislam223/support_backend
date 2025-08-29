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
        if request.method not in ("GET", "HEAD") and request.headers.get("content-length"):
            body = await request.body()
            # Сохраняем для повторного использования
            request._body = body

            try:
                decoded = body.decode("utf-8")
                if decoded.strip():
                    try:
                        request_body = json.loads(decoded)
                    except json.JSONDecodeError:
                        request_body = decoded
            except Exception:
                request_body = "<binary_data>"
    except Exception as e:
        request_body = f"<error_reading_body: {str(e)}>"

    # === Определение пользователя ===
    user = "anonymous"
    client_ip = request.client.host if request.client else "-"

    # === Обработка запроса с перехватом ответа ===
    response_body = None
    try:
        # Вызываем следующий middleware/обработчик и получаем ответ
        response = await call_next(request)

        # === ПРАВИЛЬНЫЙ ПЕРЕХВАТ ТЕЛА ОТВЕТА ===
        # Для FastAPI нужно использовать response.body только после рендеринга
        # Но лучше перехватить на уровне получения chunk'ов

        # Создаем кастомный response для перехвата
        original_response = response
        response_body_chunks = []

        async def body_iterator():
            if hasattr(original_response, "body_iterator"):
                async for chunk in original_response.body_iterator:
                    response_body_chunks.append(chunk)
                    yield chunk
            elif hasattr(original_response, "body"):
                chunk = original_response.body
                response_body_chunks.append(chunk)
                yield chunk
            else:
                yield b""

        # Создаем новый response с перехваченным body
        response = Response(
            content=body_iterator(),
            status_code=original_response.status_code,
            headers=dict(original_response.headers),
            media_type=original_response.media_type
        )

    except Exception as e:
        logger.exception("Unhandled exception in request flow")
        response = Response(
            content=json.dumps({"detail": "Internal Server Error"}),
            status_code=500,
            media_type="application/json"
        )
        response_body = {"detail": "Internal Server Error"}

    process_time = time.time() - start_time

    # === После обработки запроса извлекаем тело ответа ===
    if response_body is None and 'response_body_chunks' in locals():
        try:
            # Собираем все chunks в одно тело
            full_response_body = b"".join(response_body_chunks)
            if full_response_body:
                try:
                    decoded = full_response_body.decode("utf-8")
                    if decoded.strip():
                        try:
                            response_body = json.loads(decoded)
                        except json.JSONDecodeError:
                            response_body = decoded
                except Exception:
                    response_body = "<binary_response>"
        except Exception as e:
            response_body = f"<error_reading_response: {str(e)}>"

    # === Маскировка чувствительных данных ===
    safe_request_body = mask_sensitive_data(request_body)
    safe_response_body = mask_sensitive_data(response_body)

    # === Логирование ===
    method = request.method
    endpoint = request.url.path
    status_code = response.status_code

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