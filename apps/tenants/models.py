"""
Tenant — Universitetlar / Tashkilotlar modeli
"""
from django.db import models
from core.models import BaseModel


class Tenant(BaseModel):
    name = models.CharField(max_length=255, verbose_name='Tashkilot nomi')
    short_name = models.CharField(max_length=50, verbose_name='Qisqa nomi')
    subdomain = models.CharField(max_length=100, unique=True, verbose_name='Subdomain')
    logo = models.ImageField(upload_to='tenants/logos/', null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    contract_start = models.DateField(null=True, blank=True)
    contract_end = models.DateField(null=True, blank=True)
    max_users = models.PositiveIntegerField(default=1000)

    # AI sozlamalari (tenant darajasida override qilish mumkin)
    ai_model = models.CharField(max_length=100, blank=True)
    syllabus_match_threshold = models.PositiveSmallIntegerField(default=75)
    grading_sensitivity = models.PositiveSmallIntegerField(default=7)  # 1-10

    # Funksiyalar
    inclusive_education_enabled = models.BooleanField(default=True)
    voice_grading_enabled = models.BooleanField(default=True)
    auto_gradebook_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Tenant'
        verbose_name_plural = 'Tenantlar'
        db_table = 'tenants'

    def __str__(self):
        return f'{self.short_name} — {self.name}'
