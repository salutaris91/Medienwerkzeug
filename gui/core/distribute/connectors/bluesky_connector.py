import logging
from .base import BaseConnector, SendResult

logger = logging.getLogger(__name__)


class BlueskyConnector(BaseConnector):

    @property
    def platform_id(self) -> str:
        return 'bluesky'

    @property
    def platform_name(self) -> str:
        return 'Bluesky'

    def is_connected(self, token_config: dict) -> bool:
        return bool(token_config.get('handle') and token_config.get('app_password'))

    def send(self, text: str, platform_target: dict, token_config: dict) -> SendResult:
        if not self.is_connected(token_config):
            return {
                'success': False,
                'platform': self.platform_name,
                'message': 'Bluesky-Account nicht verknüpft.',
                'url': None
            }

        target_handle = platform_target.get('handle')
        post_text = f"@{target_handle} {text}" if target_handle else text

        try:
            from atproto import Client
            client = Client()
            client.login(token_config['handle'], token_config['app_password'])
            post = client.send_post(post_text)
            return {
                'success': True,
                'platform': self.platform_name,
                'message': 'Bluesky-Post erfolgreich.',
                'url': None
            }
        except Exception as e:
            logger.error("Bluesky post failed: %s", e)
            return {
                'success': False,
                'platform': self.platform_name,
                'message': f'Fehler beim Senden an Bluesky: {e}',
                'url': None
            }
