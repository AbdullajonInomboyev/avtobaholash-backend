"""
Core — Barcha modellarga asos bo'luvchi BaseModel
"""
import uuid
from django.db import models


class BaseModel(models.Model):
    """
    Barcha modellar shu classdan meros oladi.
    UUID, created_at, updated_at avtomatik qo'shiladi.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class TenantBaseModel(BaseModel):
    """
    Tenant (Universitet) ga tegishli modellar uchun.
    Har bir so'rovda tenant_id avtomatik filter qilinadi.
    """
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='%(class)s_set',
        db_index=True,
    )

    class Meta:
        abstract = True
