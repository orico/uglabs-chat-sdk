"""Configuration for UG Game MCP Server."""

from typing import Optional

from pydantic import BaseModel, Field


class MCPConfig(BaseModel):
    """Configuration for the MCP server."""

    service_account_api_key: Optional[str] = Field(
        default=None, description="Service account API key for UG Game authentication"
    )
    player_federated_id: Optional[str] = Field(
        default=None, description="Player federated ID for UG Game authentication"
    )
    system_prompt: Optional[str] = Field(default=None, description="System prompt for the AI")
    audio_output: bool = Field(
        default=False, description="Whether to request audio output from the AI"
    )
    debug_mode: bool = Field(default=False, description="Enable debug mode")
    sample_rate: int = Field(default=16000, description="Audio sample rate")
    language_code: str = Field(default="en", description="Language code for voice recognition")
