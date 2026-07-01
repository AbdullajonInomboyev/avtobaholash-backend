"""
Question Bank — Savol banki
O'qituvchi barcha yuklagan savollarni qayta ishlatishi mumkin
"""
from django.db import models
from core.models import TenantBaseModel


class DifficultyLevel(models.TextChoices):
    EASY = 'easy', 'Oson'
    MEDIUM = 'medium', "O'rta"
    HARD = 'hard', 'Qiyin'


class QuestionBank(TenantBaseModel):
    """Savol banki"""
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='question_bank',
    )
    subject = models.ForeignKey(
        'academics.Subject',
        on_delete=models.CASCADE,
        related_name='question_bank',
    )
    topic = models.ForeignKey(
        'syllabus.SyllabusTopic',
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    question_text = models.TextField()
    question_type = models.CharField(max_length=20)
    difficulty = models.CharField(
        max_length=10,
        choices=DifficultyLevel.choices,
        default=DifficultyLevel.MEDIUM,
    )
    # ArrayField PostgreSQL specific — SQLite uchun JSONField ishlatamiz
    tags = models.JSONField(default=list, blank=True)
    options = models.JSONField(
        default=list,
        help_text='[{"text": "...", "is_correct": true}]',
    )

    # Statistika
    usage_count = models.PositiveIntegerField(default=0)
    avg_correct_rate = models.DecimalField(
        max_digits=4, decimal_places=2,
        null=True, blank=True,
        verbose_name="O'rtacha to'g'ri javob %",
    )

    # AI takroriy savol aniqlash
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='duplicates',
    )
    similarity_score = models.DecimalField(
        max_digits=4, decimal_places=2,
        null=True, blank=True,
    )

    class Meta:
        db_table = 'question_bank'
        verbose_name = 'Savol banki'
        indexes = [
            models.Index(fields=['teacher', 'subject']),
            models.Index(fields=['is_duplicate']),
        ]

    def __str__(self):
        return f'{self.question_text[:60]}...'


class BulkImportLog(TenantBaseModel):
    """Excel import jurnali"""

    class ImportType(models.TextChoices):
        USERS = 'users', 'Foydalanuvchilar'
        STUDENTS = 'students', 'Talabalar'
        TEACHERS = 'teachers', "O'qituvchilar"
        GROUPS = 'groups', 'Guruhlar'
        QUESTIONS = 'questions', 'Savollar'

    class ImportStatus(models.TextChoices):
        PROCESSING = 'processing', 'Jarayonda'
        DONE = 'done', 'Bajarildi'
        FAILED = 'failed', 'Xato'

    imported_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='imports',
    )
    import_type = models.CharField(max_length=20, choices=ImportType.choices)
    file = models.FileField(upload_to='imports/')
    total_rows = models.PositiveIntegerField(default=0)
    success_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    error_details = models.JSONField(default=list)
    status = models.CharField(
        max_length=15,
        choices=ImportStatus.choices,
        default=ImportStatus.PROCESSING,
    )

    class Meta:
        db_table = 'bulk_import_logs'
        verbose_name = 'Import jurnali'