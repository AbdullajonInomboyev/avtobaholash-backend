"""
Accounts — Foydalanuvchilar, Rollar, Sessionlar
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from core.models import BaseModel


class Role(models.TextChoices):
    SUPER_ADMIN = 'super_admin', 'Bosh Admin'
    ADMIN = 'admin', 'Admin'
    DEPARTMENT_HEAD = 'department_head', 'Kafedra Mudiri'
    TEACHER = 'teacher', "O'qituvchi"
    STUDENT = 'student', 'Talaba'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email majburiy')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', Role.SUPER_ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    # Tenant (null = super_admin uchun)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='users',
        db_index=True,
    )

    # Shaxsiy ma'lumotlar
    first_name = models.CharField(max_length=100, verbose_name='Ism')
    last_name = models.CharField(max_length=100, verbose_name='Familiya')
    middle_name = models.CharField(max_length=100, blank=True, verbose_name='Otasining ismi')
    email = models.EmailField(unique=True, verbose_name='Email')
    phone = models.CharField(max_length=20, blank=True, verbose_name='Telefon')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    # Tashqi ID lar (HEMIS yoki boshqa tizimdan import uchun)
    employee_id = models.CharField(max_length=50, blank=True, db_index=True)
    student_id = models.CharField(max_length=50, blank=True, db_index=True)

    # Rol
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)

    # Inklyuziv ta'lim
    is_inclusive = models.BooleanField(
        default=False,
        verbose_name='Ko\'zi ojiz talaba',
        help_text='Ovozli interfeys yoqiladi'
    )

    # Telegram
    telegram_chat_id = models.BigIntegerField(null=True, blank=True, unique=True)
    telegram_username = models.CharField(max_length=100, blank=True)

    # Holat
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        verbose_name = 'Foydalanuvchi'
        verbose_name_plural = 'Foydalanuvchilar'
        db_table = 'users'
        indexes = [
            models.Index(fields=['tenant', 'role']),
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        return f'{self.last_name} {self.first_name} ({self.get_role_display()})'

    @property
    def full_name(self):
        return f'{self.last_name} {self.first_name} {self.middle_name}'.strip()

    @property
    def is_super_admin(self):
        return self.role == Role.SUPER_ADMIN

    @property
    def is_department_head(self):
        return self.role == Role.DEPARTMENT_HEAD

    @property
    def is_teacher(self):
        return self.role == Role.TEACHER

    @property
    def is_student(self):
        return self.role == Role.STUDENT


class UserSession(BaseModel):
    """Foydalanuvchi sessionlari — qurilma va IP nazorati"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    token_hash = models.CharField(max_length=500)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.JSONField(default=dict)  # {browser, os, device_type}
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'user_sessions'
        indexes = [models.Index(fields=['user', 'is_active'])]

    def __str__(self):
        return f'{self.user.email} — {self.ip_address}'


class PasswordResetToken(BaseModel):
    """Parolni tiklash tokeni"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        db_table = 'password_reset_tokens'
