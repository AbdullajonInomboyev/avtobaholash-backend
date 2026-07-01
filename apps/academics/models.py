"""
Academics — Fan, Semestr, Fan-O'qituvchi-Guruh biriktirilishi
"""
from django.db import models
from core.models import TenantBaseModel


class SubjectType(models.TextChoices):
    MANDATORY = 'mandatory', 'Majburiy'
    ELECTIVE = 'elective', 'Tanlash'
    GENERAL = 'general', "Umumta'lim"


class Subject(TenantBaseModel):
    """Fan"""
    department = models.ForeignKey(
        'organization.Department',
        on_delete=models.CASCADE,
        related_name='subjects',
    )
    name = models.CharField(max_length=255, verbose_name='Fan nomi')
    code = models.CharField(max_length=50, blank=True, verbose_name='Fan kodi')
    credit_hours = models.PositiveSmallIntegerField(default=3, verbose_name='Kredit soat')
    subject_type = models.CharField(
        max_length=20,
        choices=SubjectType.choices,
        default=SubjectType.MANDATORY,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'subjects'
        unique_together = ('tenant', 'code')
        verbose_name = 'Fan'
        verbose_name_plural = 'Fanlar'

    def __str__(self):
        return f'{self.code} — {self.name}'


class AcademicTerm(TenantBaseModel):
    """Akademik semestr"""
    name = models.CharField(max_length=100, verbose_name='Semestr nomi')
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        db_table = 'academic_terms'
        verbose_name = 'Semestr'
        verbose_name_plural = 'Semestrlar'

    def save(self, *args, **kwargs):
        # Faqat bitta semestr joriy bo'lishi mumkin
        if self.is_current:
            AcademicTerm.objects.filter(
                tenant=self.tenant, is_current=True
            ).exclude(pk=self.pk).update(is_current=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.name} ({self.tenant.short_name})'


class SubjectAssignment(TenantBaseModel):
    """
    Fan → O'qituvchi → Guruh → Semestr
    Bu jadval markaziy bog'lovchi — topshiriqlar, sillabus, jurnal shu yerga bog'lanadi
    """
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    teacher = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='teaching_assignments',
    )
    group = models.ForeignKey(
        'organization.Group',
        on_delete=models.CASCADE,
        related_name='subject_assignments',
    )
    term = models.ForeignKey(
        AcademicTerm,
        on_delete=models.CASCADE,
        related_name='subject_assignments',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'subject_assignments'
        unique_together = ('subject', 'teacher', 'group', 'term')
        verbose_name = 'Fan biriktirilishi'
        verbose_name_plural = 'Fan biriktirishlari'

    def __str__(self):
        return f'{self.subject.name} | {self.teacher.full_name} | {self.group.name}'
