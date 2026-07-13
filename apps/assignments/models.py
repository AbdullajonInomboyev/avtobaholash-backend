"""
Assignments — Topshiriqlar, Bo'limlar, Savollar, Variantlar
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import TenantBaseModel


class AssignmentType(models.TextChoices):
    TEST = 'test', 'Test'
    WRITTEN = 'written', 'Yozma ish'
    FILE = 'file', 'Fayl topshiriq'


class Assignment(TenantBaseModel):
    """Topshiriq — o'qituvchi yaratadi"""
    subject_assignment = models.ForeignKey(
        'academics.SubjectAssignment',
        on_delete=models.CASCADE,
        related_name='assignments',
    )
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='created_assignments',
    )
    title = models.CharField(max_length=500, verbose_name='Topshiriq nomi')
    description = models.TextField(blank=True)
    assignment_type = models.CharField(
        max_length=10,
        choices=AssignmentType.choices,
        verbose_name='Topshiriq turi',
    )

    # Vaqt chegaralari
    duration_minutes = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name='Vaqt (daqiqa)',
    )
    start_datetime = models.DateTimeField(verbose_name='Boshlanish vaqti')
    end_datetime = models.DateTimeField(verbose_name='Tugash vaqti')

    # Test sozlamalari
    total_questions = models.PositiveSmallIntegerField(
        null=True, blank=True,
        verbose_name='Jami savollar soni',
    )
    shuffle_questions = models.BooleanField(default=True, verbose_name='Savollarni aralashtirish')
    show_result_immediately = models.BooleanField(default=False)

    # Fayl topshiriq uchun
    allowed_file_types = models.CharField(
        max_length=200, blank=True,
        verbose_name='Ruxsat etilgan fayl turlari',
        help_text='pdf,docx,jpg (vergul bilan)',
    )
    max_file_size_mb = models.PositiveSmallIntegerField(default=10)

    # Inklyuziv ta'lim
    is_inclusive = models.BooleanField(
        default=False,
        verbose_name='Ko\'zi ojizlar uchun ovozli',
    )

    # Holat
    is_published = models.BooleanField(default=False)

    # AI tekshiruvi (O'qituvchiga ko'rinmaydi, kafedra mudiri ko'radi)
    ai_relevance_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        verbose_name='AI sillabusga moslik %',
    )
    ai_relevance_feedback = models.TextField(
        blank=True,
        verbose_name='AI izohi',
    )
    ai_checked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'assignments'
        verbose_name = 'Topshiriq'
        verbose_name_plural = 'Topshiriqlar'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject_assignment', 'is_published']),
            models.Index(fields=['start_datetime', 'end_datetime']),
        ]

    def __str__(self):
        return f'{self.title} ({self.get_assignment_type_display()})'


class AssignmentSection(TenantBaseModel):
    """
    Topshiriq bo'limi — har bir bo'lim bitta mavzudan
    Masalan: "1-mavzu: Algoritmlar" bo'limidan 5 ta savol
    """
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='sections',
    )
    title = models.CharField(max_length=255, verbose_name='Bo\'lim nomi')
    topic = models.ForeignKey(
        'syllabus.SyllabusTopic',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Mavzu',
    )
    questions_count = models.PositiveSmallIntegerField(
        default=5,
        verbose_name='Bu bo\'limdan nechta savol',
    )
    order_index = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'assignment_sections'
        ordering = ['order_index']
        verbose_name = 'Bo\'lim'
        verbose_name_plural = 'Bo\'limlar'

    def __str__(self):
        return f'{self.assignment.title} → {self.title}'


class QuestionType(models.TextChoices):
    SINGLE = 'single_choice', 'Bir javobli test'
    MULTIPLE = 'multiple_choice', 'Ko\'p javobli test'
    OPEN = 'open_ended', 'Ochiq savol'


class Question(TenantBaseModel):
    """Savol"""
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='questions',
    )
    section = models.ForeignKey(
        AssignmentSection,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='questions',
    )
    question_text = models.TextField(verbose_name='Savol matni')
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        default=QuestionType.SINGLE,
    )
    points = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=1.0,
        verbose_name='Ball',
    )
    order_index = models.PositiveSmallIntegerField(default=0)
    media = models.FileField(upload_to='questions/media/', null=True, blank=True)

    # TTS (Text-to-Speech) — Ko'zi ojizlar uchun
    # AI tekshirib, ovozda o'qish mumkinligini aniqlaydi
    is_tts_readable = models.BooleanField(
        null=True,   # None = AI hali tekshirmagan
        blank=True,
        verbose_name='Ovozda o\'qish mumkin',
    )
    tts_text = models.TextField(
        blank=True,
        verbose_name='AI tozalangan ovoz matni',
    )

    class Meta:
        db_table = 'questions'
        ordering = ['order_index']
        verbose_name = 'Savol'
        verbose_name_plural = 'Savollar'

    def __str__(self):
        return f'{self.question_text[:60]}...'


class AnswerOption(TenantBaseModel):
    """Test varianti"""
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name='options',
    )
    option_text = models.TextField(verbose_name='Variant matni')
    is_correct = models.BooleanField(default=False)
    order_index = models.PositiveSmallIntegerField(default=0)

    # TTS uchun
    is_tts_readable = models.BooleanField(null=True, blank=True)
    tts_text = models.TextField(blank=True)

    class Meta:
        db_table = 'answer_options'
        ordering = ['order_index']
        verbose_name = 'Variant'
        verbose_name_plural = 'Variantlar'

    def __str__(self):
        return f'{"✓" if self.is_correct else "✗"} {self.option_text[:50]}'