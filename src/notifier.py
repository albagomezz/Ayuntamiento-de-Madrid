"""
Sistema de Notificaciones para el Bot de Citas.
Soporta Telegram y Email.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

logger = logging.getLogger(__name__)


class Notifier:
    """Gestor de notificaciones multi-canal."""

    def __init__(self, config: dict):
        """
        Inicializa el notificador.

        Args:
            config: Diccionario con la configuración de notificaciones
        """
        self.config = config
        self.telegram_config = config.get('telegram', {})
        self.email_config = config.get('email', {})

    def send(self, message: str, is_success: bool = False) -> None:
        """
        Envía una notificación por todos los canales habilitados.

        Args:
            message: Mensaje a enviar
            is_success: Si es una notificación de éxito (cita conseguida)
        """
        if self.telegram_config.get('enabled', False):
            self._send_telegram(message)

        if self.email_config.get('enabled', False):
            subject = "🎉 ¡Cita Conseguida!" if is_success else "Bot de Citas - Actualización"
            self._send_email(subject, message)

    def _send_telegram(self, message: str) -> bool:
        """
        Envía un mensaje por Telegram.

        Args:
            message: Mensaje a enviar

        Returns:
            True si se envió correctamente
        """
        try:
            import requests

            bot_token = self.telegram_config.get('bot_token', '')
            chat_id = self.telegram_config.get('chat_id', '')

            if not bot_token or not chat_id:
                logger.warning("Telegram no configurado correctamente")
                return False

            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                logger.info("Notificación de Telegram enviada")
                return True
            else:
                logger.error(f"Error enviando Telegram: {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error enviando notificación de Telegram: {e}")
            return False

    def _send_email(self, subject: str, message: str) -> bool:
        """
        Envía un email.

        Args:
            subject: Asunto del email
            message: Cuerpo del mensaje

        Returns:
            True si se envió correctamente
        """
        try:
            smtp_server = self.email_config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = self.email_config.get('smtp_port', 587)
            sender_email = self.email_config.get('sender_email', '')
            sender_password = self.email_config.get('sender_password', '')
            recipient_email = self.email_config.get('recipient_email', '')

            if not all([sender_email, sender_password, recipient_email]):
                logger.warning("Email no configurado correctamente")
                return False

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Subject'] = subject

            # Crear cuerpo del mensaje
            body = f"""
            <html>
            <body>
                <h2>Bot de Citas - Ayuntamiento de Madrid</h2>
                <p>{message.replace(chr(10), '<br>')}</p>
                <hr>
                <small>Mensaje automático del bot de citas</small>
            </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))

            # Enviar email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            logger.info("Email enviado correctamente")
            return True

        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return False

    def test_notifications(self) -> dict:
        """
        Prueba todos los canales de notificación configurados.

        Returns:
            Diccionario con el resultado de cada canal
        """
        results = {}

        if self.telegram_config.get('enabled', False):
            results['telegram'] = self._send_telegram("🧪 Test de notificaciones - Bot de Citas")
        else:
            results['telegram'] = None

        if self.email_config.get('enabled', False):
            results['email'] = self._send_email(
                "Test - Bot de Citas",
                "Este es un mensaje de prueba del bot de citas."
            )
        else:
            results['email'] = None

        return results


class TelegramNotifier:
    """Notificador específico para Telegram (para uso independiente)."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send(self, message: str) -> bool:
        """Envía un mensaje por Telegram."""
        try:
            import requests

            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }

            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error: {e}")
            return False


class SoundNotifier:
    """Notificador por sonido del sistema."""

    @staticmethod
    def beep(times: int = 3) -> None:
        """Emite beeps del sistema."""
        try:
            import os
            for _ in range(times):
                # En Linux
                os.system('echo -e "\a"')
                # Alternativa usando print
                print('\a', end='', flush=True)
        except Exception:
            pass

    @staticmethod
    def play_sound(sound_file: str) -> None:
        """Reproduce un archivo de sonido."""
        try:
            import os
            import platform

            system = platform.system()

            if system == 'Darwin':  # macOS
                os.system(f'afplay {sound_file}')
            elif system == 'Linux':
                os.system(f'aplay {sound_file} 2>/dev/null || paplay {sound_file} 2>/dev/null')
            elif system == 'Windows':
                import winsound
                winsound.PlaySound(sound_file, winsound.SND_FILENAME)

        except Exception as e:
            logger.error(f"Error reproduciendo sonido: {e}")
