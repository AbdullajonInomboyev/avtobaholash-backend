"""
Analytics — Hisobotlar va Tahlil
Asosiy ma'lumotlar boshqa jadvallardan agregatsiya qilinadi.
Bu yerda faqat kesh va snapshot modellar.
"""
from django.db import models
from core.models import TenantBaseModel


class AnalyticsSnapshot(TenantBaseModel):
    """
    Kunlik snapshot — og'ir querylarni har safar hisoblashni kamaytiradi
    Celery beat har kecha 00:00 da yangilaydi
    """
    snapshot_date = models.DateField()
    snapshot_type = models.CharField(
        max_length=30,
        choices=[
            ('daily_summary', 'Kunlik xulosa'),
            ('teacher_performance', "O'qituvchi samaradorligi"),
            ('student_progress', 'Talaba progressi'),
            ('department_stats', 'Kafedra statistikasi'),
        ]
    )
    data = models.JSONField(default=dict)

    class Meta:
        db_table = 'analytics_snapshots'
        unique_together = ('tenant', 'snapshot_date', 'snapshot_type')
        indexes = [
            models.Index(fields=['tenant', 'snapshot_date']),
        ]
