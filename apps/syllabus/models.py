"""
Syllabus — Sillabus va Mavzular
"""
from django.db import models
from core.models import TenantBaseModel


class Syllabus(TenantBaseModel):
    """O'qituvchi yuklagan sillabus"""
    subject_assignment = models.OneToOneField(
        'academics.SubjectAssignment',
        on_delete=models.CASCADE,
        related_name='syllabus',
    )
    file = models.FileField(
        upload_to='syllabuses/',
        null=True, blank=True,
        verbose_name='Sillabus fayli (PDF/DOCX)',
    )
    file_type = models.CharField(max_length=10, blank=True)
    parsed_text = models.TextField(blank=True, verbose_name='AI o\'qigan matn')
    ai_processed = models.BooleanField(default=False)
    ai_processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'syllabuses'
        verbose_name = 'Sillabus'
        verbose_name_plural = 'Sillabuslар'

    def __str__(self):
        return f'Sillabus — {self.subject_assignment}'


class SyllabusTopic(TenantBaseModel):
    """Sillabusdan ajratilgan mavzular"""
    syllabus = models.ForeignKey(
        Syllabus,
        on_delete=models.CASCADE,
        related_name='topics',
    )
    topic_number = models.PositiveSmallIntegerField(verbose_name='Mavzu raqami')
    title = models.CharField(max_length=500, verbose_name='Mavzu nomi')
    description = models.TextField(blank=True)
    week_number = models.PositiveSmallIntegerField(null=True, blank=True)
    hours = models.PositiveSmallIntegerField(default=2)

    class Meta:
        db_table = 'syllabus_topics'
        ordering = ['topic_number']
        verbose_name = 'Mavzu'
        verbose_name_plural = 'Mavzular'

    def __str__(self):
        return f'{self.topic_number}. {self.title}'
