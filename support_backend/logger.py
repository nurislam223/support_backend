import logging
from logging.handlers import RotatingFileHandler
import os

# Настройка логгирования
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler(f"{LOG_DIR}/app.log", maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)

def log_action(user: str, action: str, details: str = ""):
    logging.info(f"[{user}] {action} | {details}")