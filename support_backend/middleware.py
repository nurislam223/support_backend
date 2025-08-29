from fastapi import Request, Response, HTTPException
from typing import Callable
import json
import time
from logger import log_request
from auth import get_current_user


async def log_requests_middleware(request: Request, call_next: Callable[..., Response]) -> Response:
    start_time = time.time()

    # Получаем тело запроса ДО обработки
    request_body = await request.body()
    decoded_request_body = ""

    if request_body:
        try:
            decoded_request_body = request_body.decode("utf-8")
            # Пробуем парсить как JSON для красивого логирования
            try:
                json_request = json.loads(decoded_request_body)
                decoded_request_body = json.dumps(json_request, ensure_ascii=False)
            except:
                pass  # Оставляем как есть если не JSON
        except Exception as e:
            decoded_request_body = f"<failed to decode request body: {str(e)}>"

    # Восстанавливаем тело запроса для дальнейшей обработки
    async def receive():
        return {'type': 'http.request', 'body': request_body}

    request._receive = receive

    # Получаем пользователя
    try:
        # Попробуем аутентифицировать пользователя для логирования
        try:
            current_user = await get_current_user(request)
            user = current_user.get("username", "-")
        except:
            user = "-"
    except:
        user = "-"

    method = request.method
    endpoint = request.url.path
    client_ip = request.client.host if request.client else "-"

    # Обрабатываем запрос
    response = await call_next(request)

    process_time = time.time() - start_time

    # Получаем тело ответа
    response_body = b""
    decoded_response_body = ""

    if hasattr(response, 'body_iterator'):
        # Для streaming responses
        async for chunk in response.body_iterator:
            response_body += chunk

        # Восстанавливаем тело ответа
        response = Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )
    elif hasattr(response, 'body'):
        # Для обычных responses
        response_body = getattr(response, 'body', b"")

    if response_body:
        try:
            decoded_response_body = response_body.decode("utf-8")
            # Пробуем парсить как JSON для красивого логирования
            try:
                json_response = json.loads(decoded_response_body)
                decoded_response_body = json.dumps(json_response, ensure_ascii=False)
            except:
                pass  # Оставляем как есть если не JSON
        except Exception as e:
            decoded_response_body = f"<failed to decode response body: {str(e)}>"

    # Формируем детали для логирования
    details = {
        "client_ip": client_ip,
        "process_time": f"{process_time:.3f}s",
        "request_headers": dict(request.headers),
        "request_body": decoded_request_body,
        "response_body": decoded_response_body,
        "response_headers": dict(response.headers)
    }

    # Логируем
    log_request(
        user=user,
        method=method,
        endpoint=endpoint,
        status=response.status_code,
        details=json.dumps(details, ensure_ascii=False)
    )

    return response