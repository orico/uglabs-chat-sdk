"""Configuration management for UG Game."""

import os
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class UGGameSettings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    developer_api_key: Optional[SecretStr] = Field(default=None, env="DEVELOPER_API_KEY")
    service_account_api_key: Optional[SecretStr] = Field(
        default=None, env="SERVICE_ACCOUNT_API_KEY"
    )
    player_federated_id: Optional[str] = Field(default=None, env="PLAYER_FEDERATED_ID")

    # API Configuration
    api_base_url: str = Field(default="https://pug.stg.uglabs.app")
    websocket_url: str = Field(default="wss://pug.stg.uglabs.app/interact")

    # Chat Configuration
    default_prompt: str = Field(
        default="You are a helpful AI assistant. Respond to user messages in a friendly and engaging way."
    )

    class Config:
        env_file = ".env" if os.path.exists(".env") else None
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = UGGameSettings()
