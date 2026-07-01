"""
AVTOBAHOLASH — Asosiy URL konfiguratsiyasi
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.utils import timezone


def health_check(request):
    """Docker healthcheck va monitoring uchun"""
    try:
        from django.db import connection
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False

    status_code = 200 if db_ok else 503
    return JsonResponse({
        'status': 'ok' if db_ok else 'error',
        'db': db_ok,
        'time': timezone.now().isoformat(),
    }, status=status_code)

API_V1 = 'api/v1/'

urlpatterns = [
    path('health/', health_check, name='health_check'),
    path('admin/', admin.site.urls),

    # Auth
    path(API_V1 + 'auth/', include('apps.accounts.urls')),

    # Tenant (Universitetlar)
    path(API_V1 + 'tenants/', include('apps.tenants.urls')),

    # Tashkilot strukturasi
    path(API_V1 + 'org/', include('apps.organization.urls')),

    # Akademik
    path(API_V1 + 'academics/', include('apps.academics.urls')),

    # Sillabus
    path(API_V1 + 'syllabus/', include('apps.syllabus.urls')),

    # Topshiriqlar
    path(API_V1 + 'assignments/', include('apps.assignments.urls')),

    # Talaba javoblari
    path(API_V1 + 'submissions/', include('apps.submissions.urls')),

    # Baholash
    path(API_V1 + 'grading/', include('apps.grading.urls')),

    # Feedback
    path(API_V1 + 'feedback/', include('apps.feedback.urls')),

    # Bildirishnomalar
    path(API_V1 + 'notifications/', include('apps.notifications.urls')),

    # Savol banki
    path(API_V1 + 'question-bank/', include('apps.question_bank.urls')),

    # Analytics / Hisobotlar
    path(API_V1 + 'analytics/', include('apps.analytics.urls')),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
