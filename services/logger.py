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
        self.logger.error(msg, exc_info=exc_info)

    def warning(self, msg):
        self.logger.warning(msg)

    def debug(self, msg):
        self.logger.debug(msg)

# Global Instance
logger = Logger()
