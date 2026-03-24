# services/logger.py

import logging
import os
from datetime import datetime

class Logger:
    def __init__(self, name="bot", log_dir="logs"):
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console Handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File Handler (Rotating logs would be better, but file handler is a start)
        log_file = os.path.join(log_dir, f"{name}_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def info(self, msg):
        self.logger.info(msg)

    def error(self, msg, exc_info=False):
        """Logs error and sends a detailed Telegram alert."""
        self.logger.error(msg, exc_info=exc_info)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert_msg = (
            f"🚨 <b>SYSTEM ERROR DETECTED</b>\n\n"
            f"⏰ <b>Timestamp:</b> <code>{timestamp}</code>\n"
            f"📑 <b>Summary:</b>\n<code>{msg}</code>\n\n"
            "🔍 <i>Please check the Heroku logs for full stack trace.</i>"
        )
        self._send_telegram_alert(alert_msg)

    def _send_telegram_alert(self, message: str):
        """Synchronously sends an alert to the admin."""
        import requests
        token = "7798265687:AAG61EtPE_SQfIwIKv8qjD1fZaes15VEBW4"
        admin_id = "1654334233"
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": admin_id, "text": message, "parse_mode": "HTML"}
        try:
            requests.post(url, json=payload, timeout=5)
        except Exception:
            pass # Avoid infinite error loops

    def warning(self, msg):
        self.logger.warning(msg)

    def debug(self, msg):
        self.logger.debug(msg)

# Global Instance
logger = Logger()
