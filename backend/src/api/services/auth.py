import os
import secrets
from fastapi import HTTPException, status, Header


class APIKeyAuth:
    def __init__(self):
        self.valid_keys = self._load_api_keys()

    @staticmethod
    def _load_api_keys() -> set:
        keys_str = os.getenv("API_KEYS", "")

        if not keys_str:
            demo_key = "demo_key"
            print(f"No API keys configured. Using demo key: {demo_key}")
            return {demo_key}

        return set(key.strip() for key in keys_str.split(",") if key.strip())

    def __call__(self, x_api_key: str = Header(..., description="API Key for authentication")):
        if x_api_key not in self.valid_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API Key",
                headers={"WWW-Authenticate": "ApiKey"}
            )

        return {
            "api_key": x_api_key,
            "authenticated": True,
            "user_type": "api_user"
        }

api_key_auth = APIKeyAuth()


def generate_api_key() -> str:
    return f"{secrets.token_urlsafe(32)}"

