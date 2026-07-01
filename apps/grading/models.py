"""
Grading — AI baholash, O'qituvchi o'zgartirishi, Jurnal
"""
from django.db import models
from core.models import TenantBaseModel


class AIGradingResult(TenantBaseModel):
    """AI baholash natijasi"""
    submission = models.ForeignKey(
        'submissions.AssignmentSubmission',
        on_delete=models.CASCADE,
        related_name='ai_grades',
    )
    # null bo'lsa — umumiy baho, bor bo'lsa — savol bo'yicha baho
    question = models.ForeignKey(
        'assignments.Question',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='ai_grades',
    )

    score = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    feedback = models.TextField(blank=True, verbose_name='AI izohi')

    # Yozma ish uchun rubrika bo'yicha baho
    rubric_breakdown = models.JSONField(
        default=dict,
        verbose_name='Rubrika bo\'yicha',
        help_text='{"mantiq": 2, "til": 4, "mosligi": 3}',
    )

    # AI ning ishonch darajasi (0-1)
    confidence = models.DecimalField(
        max_digits=4, decimal_places=3,
        default=0.0,
        verbose_name='AI ishonch darajasi',
    )
    model_used = models.CharField(max_length=100, blank=True)
    graded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ai_grading_results'
        verbose_name = 'AI baholash natijasi'
        verbose_name_plural = 'AI baholash natijalari'

    def __str__(self):
        return f'{self.submission} — {self.score}/{self.max_score}'

    @property
    def percentage(self):
        if self.max_score > 0:
            return round(float(self.score) / float(self.max_score) * 100, 1)
        return 0


class TeacherGradeOverride(TenantBaseModel):
    """O'qituvchi AI bahosini o'zgartirishi"""
    ai_grading = models.OneToOneField(
        AIGradingResult,
        on_delete=models.CASCADE,
        related_name='teacher_override',
    )
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='grade_overrides',
    )
    original_score = models.DecimalField(max_digits=5, decimal_places=2)
    new_score = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField(verbose_name='O\'zgartirish sababi')
    overridden_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'teacher_grade_overrides'
        verbose_name = 'Baho o\'zgartirishi'


class GradeChoice(models.IntegerChoices):
    TWO = 2, "2 (Qoniqarsiz)"
    THREE = 3, "3 (Qoniqarli)"
    FOUR = 4, "4 (Yaxshi)"
    FIVE = 5, "5 (A'lo)"


class Gradebook(TenantBaseModel):
    """Jurnal — O'qituvchi tasdiqlagan rasmiy baholar"""
    subject_assignment = models.ForeignKey(
        'academics.SubjectAssignment',
        on_delete=models.CASCADE,
        related_name='gradebook_entries',
    )
    student = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='grades',
    )
    assignment = models.ForeignKey(
        'assignments.Assignment',
        on_delete=models.CASCADE,
        related_name='gradebook_entries',
    )

    final_score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.PositiveSmallIntegerField(choices=GradeChoice.choices)

    is_confirmed = models.BooleanField(default=False, verbose_name='O\'qituvchi tasdiqladi')
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='confirmed_grades',
    )

    class Meta:
        db_table = 'gradebook'
        unique_together = ('subject_assignment', 'student', 'assignment')
        verbose_name = 'Jurnal yozuvi'
        verbose_name_plural = 'Jurnal'
        indexes = [
            models.Index(fields=['student', 'subject_assignment']),
        ]

    def __str__(self):
        return f'{self.student.full_name} — {self.grade}'


class TeacherEvaluationLog(TenantBaseModel):
    """
    O'qituvchi baholash jurnali
    MUHIM: O'qituvchiga ko'rinmaydi — faqat kafedra mudiri ko'radi
    """
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='evaluation_logs',
    )
    assignment = models.ForeignKey(
        'assignments.Assignment',
        on_delete=models.CASCADE,
        related_name='teacher_evaluations',
    )

    # Sillabus moslik
    syllabus_match_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        verbose_name='Sillabusga moslik %',
    )
    topics_covered = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Yoritilgan mavzular soni',
    )
    topics_out_of_syllabus = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='Sillabusdan tashqarida mavzular',
    )

    # Savol sifati
    question_quality_score = models.DecimalField(
        max_digits=4, decimal_places=2,
        null=True, blank=True,
    )

    ai_feedback = models.TextField(blank=True, verbose_name='AI izohi (kafedra uchun)')
    evaluated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'teacher_evaluation_logs'
        verbose_name = 'O\'qituvchi baholash jurnali'
        verbose_name_plural = 'O\'qituvchi baholash jurnallari'
