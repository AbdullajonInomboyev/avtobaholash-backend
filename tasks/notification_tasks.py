"""
Celery Tasks — Notification va Import
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_password_reset_email(self, user_id: str, token: str):
    """Parol tiklash emaili yuborish"""
    try:
        from django.contrib.auth import get_user_model
        from django.core.mail import send_mail
        from django.conf import settings

        User = get_user_model()
        user = User.objects.get(id=user_id)

        reset_url = f'https://avtobaholash.uz/reset-password?token={token}'
        send_mail(
            subject='Parolni tiklash — Avtobaholash',
            message=f'Hurmatli {user.full_name},\n\nParolni tiklash uchun:\n{reset_url}\n\nHavola 1 soat amal qiladi.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(f'Parol tiklash emaili yuborildi: {user.email}')
    except Exception as exc:
        logger.error(f'Email yuborishda xato: {exc}')
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def send_telegram_notification(self, user_id: str, message: str):
    """Telegram bildirishnoma"""
    try:
        from django.contrib.auth import get_user_model
        import requests
        from django.conf import settings

        User = get_user_model()
        user = User.objects.get(id=user_id)

        if not user.telegram_chat_id:
            return

        url = f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage'
        requests.post(url, json={
            'chat_id': user.telegram_chat_id,
            'text': message,
            'parse_mode': 'HTML',
        }, timeout=10)

    except Exception as exc:
        logger.error(f'Telegram xabar yuborishda xato: {exc}')
        raise self.retry(exc=exc, countdown=30)


@shared_task(bind=True)
def send_assignment_notifications(self, assignment_id: str):
    """Topshiriq yuborilganda barcha talablarga bildirishnoma"""
    try:
        from apps.assignments.models import Assignment
        from apps.submissions.models import AssignmentSubmission
        from apps.notifications.models import Notification, NotificationChannel

        assignment = Assignment.objects.select_related(
            'subject_assignment__group', 'teacher'
        ).get(id=assignment_id)

        # Guruh talabalarini olish
        from apps.organization.models import StudentGroup
        students = StudentGroup.objects.filter(
            group=assignment.subject_assignment.group,
            left_at__isnull=True,
        ).select_related('student')

        notifications = []
        submissions = []

        for sg in students:
            student = sg.student
            # Submission yaratish
            submissions.append(AssignmentSubmission(
                tenant=assignment.tenant,
                assignment=assignment,
                student=student,
            ))
            # Web bildirishnoma
            notifications.append(Notification(
                tenant=assignment.tenant,
                recipient=student,
                title=f'Yangi topshiriq: {assignment.title}',
                body=(
                    f'{assignment.teacher.full_name} tomonidan yangi topshiriq berildi.\n'
                    f'Muddat: {assignment.end_datetime.strftime("%d.%m.%Y %H:%M")}'
                ),
                notification_type='assignment',
                channel=NotificationChannel.WEB,
                link=f'/assignments/{assignment_id}/',
            ))
            # Telegram bildirishnoma (agar ulangan bo'lsa)
            if student.telegram_chat_id:
                msg = (
                    f'📚 <b>Yangi topshiriq!</b>\n\n'
                    f'Fan: {assignment.subject_assignment.subject.name}\n'
                    f'Topshiriq: {assignment.title}\n'
                    f'Muddat: {assignment.end_datetime.strftime("%d.%m.%Y %H:%M")}'
                )
                send_telegram_notification.delay(str(student.id), msg)

        AssignmentSubmission.objects.bulk_create(submissions, ignore_conflicts=True)
        Notification.objects.bulk_create(notifications)

        logger.info(f'Assignment {assignment_id}: {len(submissions)} ta talabaga yuborildi')

    except Exception as exc:
        logger.error(f'Assignment notification xato: {exc}')
        raise


@shared_task(bind=True)
def check_feedback_escalations(self):
    """
    Har soatda ishlaydi — o'qituvchi 24 soatda javob bermagan
    feedbacklarni kafedra mudiriga escalate qiladi
    """
    from django.utils import timezone
    from apps.feedback.models import Feedback, FeedbackStatus
    from apps.notifications.models import Notification

    now = timezone.now()
    # N+1 oldini olish uchun barcha kerakli ma'lumotlarni bir so'rovda olamiz
    overdue = Feedback.objects.filter(
        status=FeedbackStatus.OPEN,
        teacher_deadline__lt=now,
    ).select_related(
        'student',
        'teacher',
        'submission__assignment__subject_assignment__subject__department__head',
    )

    escalated_count = 0
    for feedback in overdue:
        dept = feedback.submission.assignment.subject_assignment.subject.department
        head = dept.head if dept else None

        if not head:
            continue

        feedback.status = FeedbackStatus.ESCALATED
        feedback.escalated_at = now
        feedback.save(update_fields=['status', 'escalated_at'])

        Notification.objects.create(
            tenant=feedback.tenant,
            recipient=head,
            title='Shikoyat eskalatsiya qilindi',
            body=(
                f'{feedback.teacher.full_name} 24 soat ichida '
                f'{feedback.student.full_name} shikoyatiga javob bermadi.'
            ),
            notification_type='escalation',
            link=f'/feedbacks/{feedback.id}/',
        )
        escalated_count += 1

    logger.info(f'Escalated {escalated_count} feedback(s)')


@shared_task(bind=True)
def process_bulk_import(self, log_id: str):
    """Excel fayldan foydalanuvchi import"""
    try:
        from apps.question_bank.models import BulkImportLog
        from services.import_.excel_importer import ExcelImporter

        log = BulkImportLog.objects.get(id=log_id)
        importer = ExcelImporter(log)
        importer.run()

    except Exception as exc:
        logger.error(f'Bulk import xato: {exc}')
        from apps.question_bank.models import BulkImportLog
        BulkImportLog.objects.filter(id=log_id).update(status='failed')
        raise


@shared_task
def deadline_reminder():
    """
    Har kuni 09:00 da ishlaydi
    2 kun qolgan topshiriqlar uchun talabaga eslatma
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.assignments.models import Assignment
    from apps.submissions.models import AssignmentSubmission, SubmissionStatus

    deadline_threshold = timezone.now() + timedelta(days=2)

    upcoming = Assignment.objects.filter(
        end_datetime__lte=deadline_threshold,
        end_datetime__gte=timezone.now(),
        is_published=True,
    )

    for assignment in upcoming:
        unsubmitted = AssignmentSubmission.objects.filter(
            assignment=assignment,
            status=SubmissionStatus.ASSIGNED,
        ).select_related('student')

        for submission in unsubmitted:
            student = submission.student
            days_left = (assignment.end_datetime - timezone.now()).days

            if student.telegram_chat_id:
                msg = (
                    f'⏰ <b>Eslatma!</b>\n\n'
                    f'{student.first_name}, <b>{assignment.title}</b> '
                    f'topshirig\'ining muddati {days_left} kun ichida tugaydi!\n'
                    f'Muddat: {assignment.end_datetime.strftime("%d.%m.%Y %H:%M")}'
                )
                send_telegram_notification.delay(str(student.id), msg)


@shared_task
def generate_daily_analytics_snapshot():
    """Har kecha 00:00 da analytics snapshotni yangilaydi"""
    from django.utils import timezone
    from apps.analytics.models import AnalyticsSnapshot
    from apps.tenants.models import Tenant

    today = timezone.now().date()

    for tenant in Tenant.objects.filter(is_active=True):
        _generate_tenant_snapshot(tenant, today)


def _generate_tenant_snapshot(tenant, date):
    from apps.analytics.models import AnalyticsSnapshot
    from apps.accounts.models import User, Role
    from apps.assignments.models import Assignment
    from apps.submissions.models import AssignmentSubmission
    from apps.grading.models import Gradebook

    data = {
        'total_students': User.objects.filter(tenant=tenant, role=Role.STUDENT, is_active=True).count(),
        'total_teachers': User.objects.filter(tenant=tenant, role=Role.TEACHER, is_active=True).count(),
        'total_assignments': Assignment.objects.filter(tenant=tenant, is_published=True).count(),
        'total_submissions': AssignmentSubmission.objects.filter(tenant=tenant, status='submitted').count(),
    }

    AnalyticsSnapshot.objects.update_or_create(
        tenant=tenant,
        snapshot_date=date,
        snapshot_type='daily_summary',
        defaults={'data': data},
    )
