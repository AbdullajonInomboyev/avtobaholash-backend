"""
Feedback — Talaba shikoyati, Escalation tizimi
"""
from django.db import models
from core.models import TenantBaseModel


class FeedbackStatus(models.TextChoices):
    OPEN = 'open', 'Ochiq'
    TEACHER_REPLIED = 'teacher_replied', "O'qituvchi javob berdi"
    ESCALATED = 'escalated', 'Kafedra mudiriga yuborildi'
    CLOSED = 'closed', 'Yopildi'


class Feedback(TenantBaseModel):
    """Talaba shikoyati"""
    submission = models.ForeignKey(
        'submissions.AssignmentSubmission',
        on_delete=models.CASCADE,
        related_name='feedbacks',
    )
    student = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='feedbacks',
    )
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='received_feedbacks',
    )
    message = models.TextField(verbose_name='Talaba shikoyati')
    status = models.CharField(
        max_length=20,
        choices=FeedbackStatus.choices,
        default=FeedbackStatus.OPEN,
    )

    # Avtomatik escalation
    teacher_deadline = models.DateTimeField(
        verbose_name='O\'qituvchi javob berish muddati',
        help_text='24 soat ichida javob bermasa kafedra mudiriga yuboriladi',
    )
    escalated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'feedbacks'
        verbose_name = 'Shikoyat'
        verbose_name_plural = 'Shikoyatlar'
        indexes = [
            models.Index(fields=['teacher', 'status']),
        ]

    def __str__(self):
        return f'{self.student.full_name} → {self.teacher.full_name} ({self.get_status_display()})'


class FeedbackResponse(TenantBaseModel):
    """Shikoyatga javob"""
    feedback = models.ForeignKey(
        Feedback,
        on_delete=models.CASCADE,
        related_name='responses',
    )
    responder = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='feedback_responses',
    )
    message = models.TextField()
    escalated_to = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='escalated_feedbacks',
        verbose_name='Kafedra mudiriga yuborildi',
    )

    class Meta:
        db_table = 'feedback_responses'
        verbose_name = 'Shikoyat javobi'
