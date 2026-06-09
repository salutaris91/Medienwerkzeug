import logging
from .base import BaseConnector, SendResult

logger = logging.getLogger(__name__)


class MastodonConnector(BaseConnector):

    @property
    def platform_id(self) -> str:
        return 'mastodon'

    @property
    def platform_name(self) -> str:
        return 'Mastodon'

    def is_connected(self, token_config: dict) -> bool:
        return bool(token_config.get('access_token') and token_config.get('instance_url'))

    def send(self, text: str, platform_target: dict, token_config: dict) -> SendResult:
        if not self.is_connected(token_config):
            return {
                'success': False,
                'platform': self.platform_name,
                'message': 'Mastodon-Account nicht verknüpft.',
                'url': None
            }

        target_handle = platform_target.get('handle')
        status_text = f"@{target_handle} {text}" if target_handle else text

        try:
            from mastodon import Mastodon
            mastodon = Mastodon(
                access_token=token_config['access_token'],
                api_base_url=token_config['instance_url']
            )
            post = mastodon.status_post(status_text, visibility='public')
            post_url = post.get('url', '')
            return {
                'success': True,
                'platform': self.platform_name,
                'message': 'Mastodon-Post erfolgreich.',
                'url': post_url
            }
        except Exception as e:
            logger.error("Mastodon post failed: %s", e)
            return {
                'success': False,
                'platform': self.platform_name,
                'message': f'Fehler beim Senden an Mastodon: {e}',
                'url': None
            }
