from fastapi import Request, Response
from typing import Callable
import json
import time
from logger import log_request
from auth import get_current_user


async def log_requests_middleware(request: Request, call_next: Callable[..., Response]) -> Response:
    start_time = time.time()

    # Получаем тело запроса ДО обработки
    request_body = await request.body()
    request_body_json = None

    if request_body:
        try:
            decoded_body = request_body.decode("utf-8")
            if decoded_body.strip():  # Если тело не пустое
                try:
                    request_body_json = json.loads(decoded_body)
                except json.JSONDecodeError:
                    request_body_json = decoded_body  # Сохраняем как текст если не JSON
        except Exception as e:
            request_body_json = f"<failed to decode: {str(e)}>"

    # Восстанавливаем тело запроса для дальнейшей обработки
    async def receive():
        return {'type': 'http.request', 'body': request_body}

    request._receive = receive

    # Получаем пользователя
    user = "-"
    try:
        current_user = await get_current_user(request)
        user = current_user.get("username", "-")
    except Exception:
        # Если аутентификация не удалась, пробуем получить из заголовков
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header and auth_header.startswith("Bearer "):
                user = "authenticated"
        except:
            pass

    method = request.method
    endpoint = request.url.path
    client_ip = request.client.host if request.client else "-"

    # Обрабатываем запрос
    response = await call_next(request)

    process_time = time.time() - start_time

    # Получаем тело ответа
    response_body_json = None

    if hasattr(response, 'body_iterator'):
        # Для streaming responses
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        # Восстанавливаем тело ответа
        response = Response(
            content=response_body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type
        )

        if response_body:
            try:
                decoded_body = response_body.decode("utf-8")
                if decoded_body.strip():
                    try:
                        response_body_json = json.loads(decoded_body)
                    except json.JSONDecodeError:
                        response_body_json = decoded_body
            except Exception as e:
                response_body_json = f"<failed to decode: {str(e)}>"

    elif hasattr(response, 'body'):
        # Для обычных responses
        response_body = getattr(response, 'body', b"")
        if response_body:
            try:
                decoded_body = response_body.decode("utf-8")
                if decoded_body.strip():
                    try:
                        response_body_json = json.loads(decoded_body)
                    except json.JSONDecodeError:
                        response_body_json = decoded_body
            except Exception as e:
                response_body_json = f"<failed to decode: {str(e)}>"

    # Формируем детали
    details = f"IP: {client_ip} | Time: {process_time:.3f}s"

    # Логируем в JSON формате
    log_request(
        user=user,
        method=method,
        endpoint=endpoint,
        status=response.status_code,
        details=details,
        request_body=request_body_json,
        response_body=response_body_json
    )

    return response