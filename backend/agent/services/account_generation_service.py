from __future__ import annotations

import secrets
import string
from datetime import datetime

from backend.core.models.auth import GeneratedAccountCredentials


class AccountGenerationService:
    def generate(self, base_domain: str = "example.test", display_name: str = "") -> GeneratedAccountCredentials:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        token = secrets.token_hex(4)
        username = f"user_{timestamp}_{token}"[:24]
        email = f"{username}@{base_domain.replace('https://', '').replace('http://', '').split('/')[0]}"
        password = self._strong_password()
        return GeneratedAccountCredentials(
            email=email,
            username=username,
            password=password,
            display_name=display_name or username,
            source="generated",
        )

    @staticmethod
    def _strong_password(length: int = 16) -> str:
        alphabet = string.ascii_letters + string.digits + "!@#$%&*"
        while True:
            password = "".join(secrets.choice(alphabet) for _ in range(length))
            if (
                any(char.islower() for char in password)
                and any(char.isupper() for char in password)
                and any(char.isdigit() for char in password)
                and any(char in "!@#$%&*" for char in password)
            ):
                return password
