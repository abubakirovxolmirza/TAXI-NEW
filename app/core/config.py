from __future__ import annotations

from functools import lru_cache
from typing import List, Optional

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(..., alias="DATABASE_URL")

    click_service_id: int = Field(..., alias="CLICK_SERVICE_ID")
    click_merchant_id: int = Field(..., alias="CLICK_MERCHANT_ID")
    click_secret_key: str = Field(..., alias="CLICK_SECRET_KEY")
    click_merchant_user_id: Optional[int] = Field(default=None, alias="CLICK_MERCHANT_USER_ID")
    click_verify_signature: bool = Field(default=True, alias="CLICK_VERIFY_SIGNATURE")
    click_disable_sign_check: bool = Field(default=False, alias="CLICK_DISABLE_SIGN_CHECK")

    click_allowed_ips_raw: Optional[str] = Field(default=None, alias="CLICK_ALLOWED_IPS")

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        populate_by_name=True,
        extra="ignore",
    )

    @computed_field
    @property
    def click_allowed_ips(self) -> List[str]:
        if not self.click_allowed_ips_raw:
            return []
        return [item.strip() for item in self.click_allowed_ips_raw.split(",") if item.strip()]

    @computed_field
    @property
    def async_database_url(self) -> str:
        url = self.database_url
        if url.startswith("postgresql+asyncpg://"):
            return url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
