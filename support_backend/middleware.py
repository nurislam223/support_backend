# middleware.py
from fastapi import Request, Response
from fastapi.responses import StreamingResponse
from typing import Callable
import json
import time
from logger import log_request, mask_sensitive_data  # <-- Добавим функцию маскировки
import asyncio


async def log_requests_middleware(request: Request, call_next: Callable) -> Response:
    start_time = time.time()

    # === Захват тела запроса ===
    try:
        body = await request.body()
        request._body = body  # Кэшируем для повторного доступа
    except Exception as e:
        body = b""

    request_body_json = None
    if body:
        try:
            decoded = body.decode("utf-8")
            if decoded.strip():
                try:
                    request_body_json = json.loads(decoded)
                except json.JSONDecodeError:
                    request_body_json = decoded  # как строка
        except Exception as e:
            request_body_json = f"<decode_error: {str(e)}>"

    # Восстанавливаем тело для повторного чтения
    async def receive():
        return {"type": "http.request", "body": body}

    request._receive = receive

    # === Определение пользователя ===
    user = "-"
    try:
        current_user_data = await request.app.dependency_overrides.get(
            "get_current_user", get_current_user
        )(request)
        user = current_user_data.get("username", "-")
    except Exception:
        try:
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                user = "authenticated"
        except:
            pass

    method = request.method
    endpoint = request.url.path
    client_ip = request.client.host if request.client else "-"

    # === Перехват ответа через обёртку send ===
    response_body = []

    async def send_wrapper(message):
        if message["type"] == "http.response.body":
            if message.get("body"):
                response_body.append(message["body"])
        elif message["type"] == "http.response.chunk":
            if message.get("chunk"):
                response_body.append(message["chunk"])
        await request.scope["fastapi.original_send"](message)

    # Сохраняем оригинальный send
    response_body = []

    async def send_wrapper(message):
        if message["type"] == "http.response.body":
            if message.get("body"):
                response_body.append(message["body"])
        elif message["type"] == "http.response.chunk":
            if message.get("chunk"):
                response_body.append(message["chunk"])
        await original_send(message)

    # Только если 'send' присутствует в scope
    if "send" not in request.scope:
        # Нет send — вероятно, фоновая задача или предзагрузка
        return await call_next(request)

    original_send = request.scope["send"]

    # Устанавливаем обёртку только один раз
    if "fastapi.original_send" not in request.scope:
        request.scope["fastapi.original_send"] = original_send
        request.scope["send"] = send_wrapper

    # === Обработка запроса ===
    try:
        response = await call_next(request)
    except Exception as e:
        # На всякий случай логируем ошибку и возвращаем 500
        import logging
        logging.getLogger("app").exception("Unhandled exception in request flow")
        response = Response(
            content=json.dumps({"detail": "Internal Server Error"}),
            status_code=500,
            media_type="application/json"
        )

    # === Собираем тело ответа ===
    response_body_bytes = b"".join(response_body)
    response_body_json = None

    if response_body_bytes:
        try:
            decoded = response_body_bytes.decode("utf-8")
            if decoded.strip():
                try:
                    response_body_json = json.loads(decoded)
                except json.JSONDecodeError:
                    response_body_json = decoded
        except Exception as e:
            response_body_json = f"<decode_error: {str(e)}>"

    process_time = time.time() - start_time

    # === Маскировка чувствительных данных ===
    safe_request_body = mask_sensitive_data(request_body_json)
    safe_response_body = mask_sensitive_data(response_body_json)

    # === Логирование ===
    details = f"client_ip: {client_ip}, process_time: {process_time:.3f}s"
    log_request(
        user=user,
        method=method,
        endpoint=endpoint,
        status=response.status_code,
        details=details,
        request_body=safe_request_body,
        response_body=safe_response_body
    )

    return response