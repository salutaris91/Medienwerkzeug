from abc import ABC, abstractmethod
from typing import Optional, TypedDict


class SendResult(TypedDict):
    success: bool
    platform: str
    message: str
    url: Optional[str]


class BaseConnector(ABC):

    @property
    @abstractmethod
    def platform_id(self) -> str:
        pass

    @property
    @abstractmethod
    def platform_name(self) -> str:
        pass

    @abstractmethod
    def is_connected(self, token_config: dict) -> bool:
        """True if the given token config has all required fields."""
        pass

    @abstractmethod
    def send(self, text: str, platform_target: dict, token_config: dict) -> SendResult:
        """
        Send text to the platform.
        platform_target: the politician's platform data (handle, contact_form, etc.)
        token_config: the user's stored OAuth tokens/credentials for this platform
        """
        pass
