"""
Notifications — Web va Telegram bildirishnomalar
"""
from django.db import models
from core.models import TenantBaseModel


class NotificationType(models.TextChoices):
    ASSIGNMENT = 'assignment', 'Yangi topshiriq'
    DEADLINE = 'deadline', 'Muddat yaqinlashdi'
    GRADE = 'grade', 'Baho qo\'yildi'
    FEEDBACK = 'feedback', 'Shikoyat'
    ESCALATION = 'escalation', 'Escalation'
    SYSTEM = 'system', 'Tizim xabari'


class NotificationChannel(models.TextChoices):
    WEB = 'web', 'Web'
    TELEGRAM = 'telegram', 'Telegram'
    SMS = 'sms', 'SMS'


class Notification(TenantBaseModel):
    """Bildirishnoma"""
    recipient = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    title = models.CharField(max_length=500)
    body = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NotificationType.choices)
    channel = models.CharField(
        max_length=10,
        choices=NotificationChannel.choices,
        default=NotificationChannel.WEB,
    )

    # Havola (ixtiyoriy)
    link = models.CharField(max_length=500, blank=True)

    is_read = models.BooleanField(default=False)
    sent_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    # Telegram
    telegram_message_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-sent_at']
        verbose_name = 'Bildirishnoma'
        verbose_name_plural = 'Bildirishnomalar'
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f'{self.recipient.full_name} — {self.title}'
