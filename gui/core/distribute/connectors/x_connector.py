import logging
from .base import BaseConnector, SendResult

logger = logging.getLogger(__name__)

MAX_TWEET_LENGTH = 280


class XConnector(BaseConnector):

    @property
    def platform_id(self) -> str:
        return 'x'

    @property
    def platform_name(self) -> str:
        return 'X (Twitter)'

    def is_connected(self, token_config: dict) -> bool:
        return bool(token_config.get('access_token') and token_config.get('refresh_token'))

    def send(self, text: str, platform_target: dict, token_config: dict) -> SendResult:
        if not self.is_connected(token_config):
            return {
                'success': False,
                'platform': self.platform_name,
                'message': 'X-Account nicht verknüpft. Bitte unter Einstellungen verbinden.',
                'url': None
            }

        handle = platform_target.get('handle', '')
        tweet_text = f"@{handle} {text}" if handle else text

        if len(tweet_text) > MAX_TWEET_LENGTH:
            tweet_text = tweet_text[:MAX_TWEET_LENGTH - 1] + '…'

        try:
            import tweepy
            client = tweepy.Client(access_token=token_config['access_token'])
            response = client.create_tweet(text=tweet_text)
            tweet_id = response.data['id']
            return {
                'success': True,
                'platform': self.platform_name,
                'message': 'Tweet erfolgreich gesendet.',
                'url': f'https://x.com/i/web/status/{tweet_id}'
            }
        except Exception as e:
            logger.error("X post failed: %s", e)
            return {
                'success': False,
                'platform': self.platform_name,
                'message': f'Fehler beim Senden an X: {e}',
                'url': None
            }
