"""
Submissions — Talaba javoblari, Anti-cheat monitoring
"""
from django.db import models
from core.models import TenantBaseModel


class SubmissionStatus(models.TextChoices):
    ASSIGNED = 'assigned', 'Topshirilmagan'
    STARTED = 'started', 'Boshlangan'
    SUBMITTED = 'submitted', 'Topshirilgan'
    GRADED = 'graded', 'Baholangan'
    EXPIRED = 'expired', 'Muddati o\'tgan'


class AssignmentSubmission(TenantBaseModel):
    """Talabaning topshiriqni bajarish holati"""
    assignment = models.ForeignKey(
        'assignments.Assignment',
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    student = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='submissions',
    )
    status = models.CharField(
        max_length=15,
        choices=SubmissionStatus.choices,
        default=SubmissionStatus.ASSIGNED,
    )

    # Vaqt
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_spent_seconds = models.PositiveIntegerField(default=0)

    # Qurilma ma'lumotlari
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.JSONField(default=dict)

    # Anti-cheat blok
    is_locked = models.BooleanField(default=False)
    lock_reason = models.TextField(blank=True)
    tab_switch_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'assignment_submissions'
        unique_together = ('assignment', 'student')
        verbose_name = 'Topshiriq javobi'
        verbose_name_plural = 'Topshiriq javoblari'
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['assignment', 'status']),
        ]

    def __str__(self):
        return f'{self.student.full_name} — {self.assignment.title} ({self.get_status_display()})'


class SubmissionAnswer(TenantBaseModel):
    """Talabaning har bir savolga javobi"""
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='answers',
    )
    question = models.ForeignKey(
        'assignments.Question',
        on_delete=models.CASCADE,
        related_name='student_answers',
    )

    # Javob turiga qarab biri to'ldiriladi
    selected_options = models.ManyToManyField(
        'assignments.AnswerOption',
        blank=True,
        verbose_name='Tanlangan variantlar',
    )
    text_answer = models.TextField(blank=True, verbose_name='Yozma javob')
    file_answer = models.FileField(
        upload_to='submission_files/',
        null=True, blank=True,
        verbose_name='Yuklangan fayl',
    )
    voice_answer = models.FileField(
        upload_to='submission_voice/',
        null=True, blank=True,
        verbose_name='Ovozli javob',
    )

    answered_at = models.DateTimeField(auto_now=True)
    time_spent_seconds = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'submission_answers'
        unique_together = ('submission', 'question')
        verbose_name = 'Savol javobi'
        verbose_name_plural = 'Savol javoblari'


class AntiCheatEventType(models.TextChoices):
    TAB_SWITCH = 'tab_switch', 'Tab almashtirildi'
    SCREEN_SHARE = 'screen_share', 'Ekran ulashildi'
    FAST_ANSWER = 'fast_answer', 'Juda tez javob (copy-paste shubhasi)'
    MULTI_IP = 'multi_ip', 'Bir vaqtda ikki joydan kirish'
    COPY_PASTE = 'copy_paste', 'Nusxa olish/qo\'yish'
    BLUR = 'blur', 'Brauzer fokusdan chiqdi'


class AntiCheatSeverity(models.TextChoices):
    LOW = 'low', 'Past'
    MEDIUM = 'medium', 'O\'rta'
    HIGH = 'high', 'Yuqori'


class AntiCheatLog(TenantBaseModel):
    """Anti-cheat hodisalari jurnali"""
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='anti_cheat_logs',
    )
    student = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='anti_cheat_logs',
    )
    event_type = models.CharField(max_length=20, choices=AntiCheatEventType.choices)
    event_data = models.JSONField(default=dict)
    severity = models.CharField(
        max_length=10,
        choices=AntiCheatSeverity.choices,
        default=AntiCheatSeverity.LOW,
    )
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'anti_cheat_logs'
        verbose_name = 'Anti-cheat hodisa'
        verbose_name_plural = 'Anti-cheat hodisalar'
        indexes = [
            models.Index(fields=['submission', 'severity']),
        ]

    def __str__(self):
        return f'{self.student.full_name} — {self.get_event_type_display()}'
