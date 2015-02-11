from django.core.exceptions import ImproperlyConfigured
from django.db.models import get_app
import logging
from rdrf.utils import get_user, get_users

logger = logging.getLogger("registry_log")

class NotificationChannel:
    EMAIL = "email"
    SYSTEM = "system"
    SMS = "sms"

class Notifier(object):
    def send_notification(self, from_user_name, to_username, html_content):
        pass



