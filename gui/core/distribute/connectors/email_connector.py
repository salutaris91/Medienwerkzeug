import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .base import BaseConnector, SendResult

logger = logging.getLogger(__name__)


class EmailConnector(BaseConnector):

    @property
    def platform_id(self) -> str:
        return 'email'

    @property
    def platform_name(self) -> str:
        return 'E-Mail'

    def is_connected(self, token_config: dict) -> bool:
        return bool(
            token_config.get('smtp_host')
            and token_config.get('smtp_user')
            and token_config.get('smtp_password')
            and token_config.get('from_address')
        )

    def send(self, text: str, platform_target: dict, token_config: dict) -> SendResult:
        if not self.is_connected(token_config):
            return {
                'success': False,
                'platform': self.platform_name,
                'message': 'E-Mail nicht konfiguriert. Bitte unter Einstellungen SMTP-Daten eintragen.',
                'url': None
            }

        recipient = platform_target.get('address')
        contact_form = platform_target.get('contact_form')

        if not recipient:
            return {
                'success': False,
                'platform': self.platform_name,
                'message': f'Keine direkte E-Mail-Adresse hinterlegt. Kontaktformular: {contact_form}',
                'url': contact_form
            }

        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = 'Bürgeranliegen'
            msg['From'] = token_config['from_address']
            msg['To'] = recipient
            msg.attach(MIMEText(text, 'plain', 'utf-8'))

            host = token_config['smtp_host']
            port = int(token_config.get('smtp_port', 587))

            with smtplib.SMTP(host, port) as server:
                server.starttls()
                server.login(token_config['smtp_user'], token_config['smtp_password'])
                server.send_message(msg)

            logger.info("Email sent to %s via %s", recipient, host)
            return {
                'success': True,
                'platform': self.platform_name,
                'message': f'E-Mail erfolgreich an {recipient} gesendet.',
                'url': None
            }
        except Exception as e:
            logger.error("Email send failed: %s", e)
            return {
                'success': False,
                'platform': self.platform_name,
                'message': f'E-Mail-Versand fehlgeschlagen: {e}',
                'url': None
            }
