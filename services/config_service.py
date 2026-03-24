# services/config_service.py

from database.manager import db

class ConfigService:
    @staticmethod
    def get(key: str, default: str = None) -> str:
        """Fetch setting from DB, then from environment if missing/empty."""
        import os
        val = db.get_setting(key)
        if not val or val.strip() == "":
            return os.getenv(key, default)
        return val

    @staticmethod
    def set(key: str, value: str):
        db.set_setting(key, value)

    # Specific common keys
    @property
    def telegram_token(self):
        return "7798265687:AAG61EtPE_SQfIwIKv8qjD1fZaes15VEBW4"

    @property
    def admin_id(self):
        return "1654334233"

    @property
    def groq_key(self):
        return self.get("GROQ_API_KEY")

# Global Instance
config = ConfigService()
