"""
Organization — Fakultet, Kafedra, Guruh
"""
from django.db import models
from core.models import TenantBaseModel


class Faculty(TenantBaseModel):
    """Fakultet"""
    name = models.CharField(max_length=255, verbose_name='Fakultet nomi')
    code = models.CharField(max_length=20, blank=True, verbose_name='Kodi')
    dean = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='faculty_as_dean',
        verbose_name='Dekan',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'faculties'
        unique_together = ('tenant', 'code')
        verbose_name = 'Fakultet'
        verbose_name_plural = 'Fakultetlar'

    def __str__(self):
        return self.name


class Department(TenantBaseModel):
    """Kafedra"""
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='departments',
        verbose_name='Fakultet',
    )
    name = models.CharField(max_length=255, verbose_name='Kafedra nomi')
    code = models.CharField(max_length=20, blank=True)
    head = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='department_as_head',
        verbose_name='Kafedra mudiri',
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'departments'
        unique_together = ('tenant', 'code')
        verbose_name = 'Kafedra'
        verbose_name_plural = 'Kafedralar'

    def __str__(self):
        return self.name


class EducationForm(models.TextChoices):
    FULL_TIME = 'full_time', 'Kunduzgi'
    PART_TIME = 'part_time', 'Sirtqi'
    EVENING = 'evening', 'Kechki'


class Group(TenantBaseModel):
    """Talabalar guruhi"""
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='groups',
        verbose_name='Kafedra',
    )
    name = models.CharField(max_length=100, verbose_name='Guruh nomi')
    year = models.PositiveSmallIntegerField(verbose_name='O\'quv yili')
    education_form = models.CharField(
        max_length=20,
        choices=EducationForm.choices,
        default=EducationForm.FULL_TIME,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'groups'
        unique_together = ('tenant', 'name', 'year')
        verbose_name = 'Guruh'
        verbose_name_plural = 'Guruhlar'

    def __str__(self):
        return f'{self.name} ({self.year})'


class StudentGroup(TenantBaseModel):
    """Talaba — Guruh bog'lanishi (tarix bilan)"""
    student = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='student_groups',
    )
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='student_memberships',
    )
    joined_at = models.DateField(auto_now_add=True)
    left_at = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'student_groups'
        unique_together = ('student', 'group')

    @property
    def is_current(self):
        return self.left_at is None
