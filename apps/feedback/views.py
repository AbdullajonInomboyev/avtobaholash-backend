from core.utils import get_tenant
"""
Feedback — Talaba shikoyati, Escalation
"""
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response

from core.permissions import IsStudent, IsTeacher, IsDepartmentHead
from .models import Feedback, FeedbackResponse, FeedbackStatus


class FeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    assignment_title = serializers.CharField(
        source='submission.assignment.title', read_only=True
    )
    responses_count = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = [
            'id', 'student', 'student_name', 'teacher', 'teacher_name',
            'assignment_title', 'message', 'status', 'teacher_deadline',
            'escalated_at', 'responses_count', 'created_at',
        ]
        read_only_fields = ['id', 'teacher', 'status', 'teacher_deadline', 'escalated_at', 'created_at']

    def get_responses_count(self, obj):
        return obj.responses.count()


class FeedbackResponseSerializer(serializers.ModelSerializer):
    responder_name = serializers.CharField(source='responder.full_name', read_only=True)

    class Meta:
        model = FeedbackResponse
        fields = ['id', 'responder', 'responder_name', 'message', 'created_at']
        read_only_fields = ['id', 'responder', 'created_at']


# ══════════════════════════════════════════════════════════
# TALABA
# ══════════════════════════════════════════════════════════

class StudentFeedbackListCreateView(APIView):
    permission_classes = [IsStudent]

    def get(self, request):
        feedbacks = Feedback.objects.filter(
            tenant=get_tenant(request),
            student=request.user,
        ).select_related('teacher', 'submission__assignment').order_by('-created_at')
        return Response({'success': True, 'data': FeedbackSerializer(feedbacks, many=True).data})

    def post(self, request):
        from apps.submissions.models import AssignmentSubmission
        submission_id = request.data.get('submission_id')
        message = request.data.get('message', '').strip()

        if not message:
            return Response({'success': False, 'message': 'Xabar bo\'sh'}, status=400)

        submission = AssignmentSubmission.objects.filter(
            tenant=get_tenant(request),
            id=submission_id,
            student=request.user,
        ).select_related('assignment__teacher').first()

        if not submission:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)

        # Bir topshiriq uchun faqat bitta shikoyat
        if Feedback.objects.filter(submission=submission, student=request.user).exists():
            return Response({'success': False, 'message': 'Bu topshiriq uchun shikoyat allaqachon yuborilgan'}, status=400)

        feedback = Feedback.objects.create(
            tenant=get_tenant(request),
            submission=submission,
            student=request.user,
            teacher=submission.assignment.teacher,
            message=message,
            teacher_deadline=timezone.now() + timedelta(hours=24),
        )

        # O'qituvchiga bildirishnoma
        from apps.notifications.models import Notification
        Notification.objects.create(
            tenant=get_tenant(request),
            recipient=submission.assignment.teacher,
            title='Yangi shikoyat',
            body=f'{request.user.full_name} bahosiga shikoyat qildi: {submission.assignment.title}',
            notification_type='feedback',
            link=f'/feedbacks/{feedback.id}/',
        )

        return Response({'success': True, 'data': FeedbackSerializer(feedback).data},
                        status=status.HTTP_201_CREATED)


# ══════════════════════════════════════════════════════════
# O'QITUVCHI
# ══════════════════════════════════════════════════════════

class TeacherFeedbackListView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request):
        feedbacks = Feedback.objects.filter(
            tenant=get_tenant(request),
            teacher=request.user,
        ).select_related('student', 'submission__assignment').order_by('-created_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            feedbacks = feedbacks.filter(status=status_filter)

        return Response({'success': True, 'data': FeedbackSerializer(feedbacks, many=True).data})


class FeedbackReplyView(APIView):
    permission_classes = [IsTeacher]

    def post(self, request, pk):
        feedback = Feedback.objects.filter(
            tenant=get_tenant(request),
            id=pk,
            teacher=request.user,
        ).first()
        if not feedback:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)

        message = request.data.get('message', '').strip()
        if not message:
            return Response({'success': False, 'message': 'Xabar bo\'sh'}, status=400)

        response = FeedbackResponse.objects.create(
            tenant=get_tenant(request),
            feedback=feedback,
            responder=request.user,
            message=message,
        )

        feedback.status = FeedbackStatus.TEACHER_REPLIED
        feedback.save(update_fields=['status'])

        # Talabaga bildirishnoma
        from apps.notifications.models import Notification
        Notification.objects.create(
            tenant=get_tenant(request),
            recipient=feedback.student,
            title='Shikoyatingizga javob',
            body=f'{request.user.full_name} shikoyatingizga javob berdi',
            notification_type='feedback',
        )

        return Response({'success': True, 'data': FeedbackResponseSerializer(response).data})


# ══════════════════════════════════════════════════════════
# KAFEDRA MUDIRI
# ══════════════════════════════════════════════════════════

class DepartmentFeedbackListView(APIView):
    permission_classes = [IsDepartmentHead]

    def get(self, request):
        from apps.organization.models import Department
        dept = Department.objects.filter(head=request.user).first()
        if not dept:
            return Response({'success': False, 'message': 'Kafedra topilmadi'}, status=404)

        feedbacks = Feedback.objects.filter(
            tenant=get_tenant(request),
            submission__assignment__subject_assignment__subject__department=dept,
        ).select_related('student', 'teacher', 'submission__assignment').order_by('-created_at')

        return Response({'success': True, 'data': FeedbackSerializer(feedbacks, many=True).data})


# ── URLs ──────────────────────────────────────────────────
from django.urls import path

urlpatterns = [
    path('my/', StudentFeedbackListCreateView.as_view()),
    path('teacher/', TeacherFeedbackListView.as_view()),
    path('<uuid:pk>/reply/', FeedbackReplyView.as_view()),
    path('department/', DepartmentFeedbackListView.as_view()),
]