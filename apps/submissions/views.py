from core.utils import get_tenant
"""
Submissions — Javob yuborish, Anti-cheat, O'qituvchi monitoring
"""
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from core.permissions import IsStudent, IsTeacher, IsDepartmentHead
from .models import AssignmentSubmission, SubmissionAnswer, AntiCheatLog, SubmissionStatus


# ══════════════════════════════════════════════════════════
# SERIALIZERS
# ══════════════════════════════════════════════════════════

class AnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    selected_option_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False, default=list
    )
    text_answer = serializers.CharField(required=False, allow_blank=True)
    time_spent_seconds = serializers.IntegerField(
        required=False, default=0, min_value=0, max_value=86400  # max 24 soat
    )

    def validate(self, data):
        if not data.get('selected_option_ids') and not data.get('text_answer'):
            raise serializers.ValidationError('Javob bo\'sh bo\'lmasin')
        return data


class FileAnswerSubmitSerializer(serializers.Serializer):
    question_id = serializers.UUIDField()
    file_answer = serializers.FileField()

    def validate_file_answer(self, value):
        if value.size > 50 * 1024 * 1024:  # 50MB
            raise serializers.ValidationError('Fayl hajmi 50MB dan oshmasin')
        return value


class SubmissionStatusSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    anti_cheat_summary = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentSubmission
        fields = [
            'id', 'assignment', 'assignment_title', 'student',
            'status', 'started_at', 'submitted_at', 'time_spent_seconds',
            'tab_switch_count', 'is_locked', 'lock_reason', 'anti_cheat_summary',
        ]

    def get_anti_cheat_summary(self, obj):
        # prefetch_related('anti_cheat_logs') ishlatilishi shart
        logs = obj.anti_cheat_logs.all()
        total = len(logs)  # DB ga yana so'rov yubormaslik uchun
        high = sum(1 for l in logs if l.severity == 'high')
        return {'total_events': total, 'high_severity': high}


class AntiCheatLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AntiCheatLog
        fields = ['id', 'event_type', 'event_data', 'severity', 'occurred_at']


# ══════════════════════════════════════════════════════════
# VIEWS — TALABA
# ══════════════════════════════════════════════════════════

class SubmitAnswerView(APIView):
    """Savolga javob yuborish (test va yozma ish)"""
    permission_classes = [IsStudent]

    def post(self, request, submission_pk):
        submission = AssignmentSubmission.objects.filter(
            tenant=get_tenant(request),
            id=submission_pk,
            student=request.user,
            status=SubmissionStatus.STARTED,
        ).select_related('assignment').first()

        if not submission:
            return Response({'success': False, 'message': 'Topilmadi yoki boshlash kerak'}, status=404)
        if submission.is_locked:
            return Response({'success': False, 'message': 'Bloklangan'}, status=403)
        if timezone.now() > submission.assignment.end_datetime:
            return Response({'success': False, 'message': 'Vaqt tugadi'}, status=400)

        serializer = AnswerSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        answer, _ = SubmissionAnswer.objects.get_or_create(
            tenant=get_tenant(request),
            submission=submission,
            question_id=data['question_id'],
        )

        # Javobni saqlash
        if data.get('selected_option_ids'):
            answer.selected_options.set(data['selected_option_ids'])
        if data.get('text_answer'):
            answer.text_answer = data['text_answer']

        answer.time_spent_seconds = data.get('time_spent_seconds', 0)
        answer.save()

        # Anti-cheat: juda tez javob
        from django.conf import settings
        threshold = settings.ANTI_CHEAT.get('FAST_ANSWER_THRESHOLD_SECONDS', 3)
        if answer.time_spent_seconds < threshold and answer.time_spent_seconds > 0:
            AntiCheatLog.objects.create(
                tenant=get_tenant(request),
                submission=submission,
                student=request.user,
                event_type='fast_answer',
                event_data={'seconds': answer.time_spent_seconds},
                severity='medium',
            )

        return Response({'success': True, 'message': 'Javob saqlandi'})


class SubmitFileAnswerView(APIView):
    """Fayl javob yuborish"""
    permission_classes = [IsStudent]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, submission_pk):
        submission = AssignmentSubmission.objects.filter(
            tenant=get_tenant(request),
            id=submission_pk,
            student=request.user,
            status=SubmissionStatus.STARTED,
        ).first()

        if not submission:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)

        serializer = FileAnswerSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Fayl turini tekshirish
        assignment = submission.assignment
        if assignment.allowed_file_types:
            allowed = assignment.allowed_file_types.split(',')
            file = serializer.validated_data['file_answer']
            ext = file.name.split('.')[-1].lower()
            if ext not in allowed:
                return Response({
                    'success': False,
                    'message': f'Faqat {", ".join(allowed)} formatlarga ruxsat',
                }, status=400)

        answer, _ = SubmissionAnswer.objects.get_or_create(
            tenant=get_tenant(request),
            submission=submission,
            question_id=serializer.validated_data['question_id'],
        )
        answer.file_answer = serializer.validated_data['file_answer']
        answer.save()

        return Response({'success': True, 'message': 'Fayl yuklandi'})


class FinalSubmitView(APIView):
    """Topshiriqni yakunlash (submit)"""
    permission_classes = [IsStudent]

    def post(self, request, submission_pk):
        from django.db import transaction

        with transaction.atomic():
            submission = AssignmentSubmission.objects.select_for_update().filter(
                tenant=get_tenant(request),
                id=submission_pk,
                student=request.user,
                status=SubmissionStatus.STARTED,
            ).first()

            if not submission:
                return Response({'success': False, 'message': 'Topilmadi yoki allaqachon topshirilgan'}, status=404)

            now = timezone.now()
            submission.status = SubmissionStatus.SUBMITTED
            submission.submitted_at = now
            if submission.started_at:
                submission.time_spent_seconds = int((now - submission.started_at).total_seconds())
            submission.save(update_fields=['status', 'submitted_at', 'time_spent_seconds'])

        # AI baholash (async — transaction tashqarisida)
        from tasks.ai_tasks import ai_grade_submission, ai_check_plagiarism
        ai_grade_submission.delay(str(submission.id))
        ai_check_plagiarism.delay(str(submission.id))

        return Response({
            'success': True,
            'message': 'Topshiriq yuborildi. AI baholash boshlanmoqda...',
        })


class AntiCheatEventView(APIView):
    """Anti-cheat hodisalarini log qilish (frontend yuboradi)"""
    permission_classes = [IsStudent]

    def post(self, request, submission_pk):
        submission = AssignmentSubmission.objects.filter(
            tenant=get_tenant(request),
            id=submission_pk,
            student=request.user,
        ).first()
        if not submission:
            return Response({'success': False}, status=404)

        event_type = request.data.get('event_type')
        if event_type not in ['tab_switch', 'blur', 'copy_paste']:
            return Response({'success': False, 'message': 'Noto\'g\'ri hodisa turi'}, status=400)

        severity_map = {'tab_switch': 'high', 'blur': 'low', 'copy_paste': 'high'}

        AntiCheatLog.objects.create(
            tenant=get_tenant(request),
            submission=submission,
            student=request.user,
            event_type=event_type,
            event_data=request.data.get('data', {}),
            severity=severity_map.get(event_type, 'low'),
        )

        if event_type == 'tab_switch':
            from django.conf import settings
            submission.tab_switch_count += 1
            submission.save(update_fields=['tab_switch_count'])
            max_sw = settings.ANTI_CHEAT.get('MAX_TAB_SWITCHES', 2)
            if submission.tab_switch_count >= max_sw:
                submission.is_locked = True
                submission.lock_reason = f'Tab {submission.tab_switch_count} marta almashtirildi'
                submission.save(update_fields=['is_locked', 'lock_reason'])
                return Response({'success': True, 'locked': True, 'reason': submission.lock_reason})

        return Response({'success': True, 'locked': False})


# ══════════════════════════════════════════════════════════
# VIEWS — O'QITUVCHI
# ══════════════════════════════════════════════════════════

class TeacherSubmissionsView(APIView):
    """O'qituvchining topshirig'i bo'yicha barcha talaba javoblari"""
    permission_classes = [IsTeacher]

    def get(self, request, assignment_pk):
        submissions = AssignmentSubmission.objects.filter(
            tenant=get_tenant(request),
            assignment_id=assignment_pk,
            assignment__teacher=request.user,
        ).select_related('student').prefetch_related('anti_cheat_logs')
        serializer = SubmissionStatusSerializer(submissions, many=True)

        # Statistika
        total = submissions.count()
        submitted = submissions.filter(status__in=['submitted', 'graded']).count()
        graded = submissions.filter(status='graded').count()

        return Response({
            'success': True,
            'stats': {
                'total': total,
                'submitted': submitted,
                'graded': graded,
                'pending': total - submitted,
            },
            'data': serializer.data,
        })


class SubmissionDetailView(APIView):
    """Bitta submission tafsilotlari (o'qituvchi uchun)"""
    permission_classes = [IsTeacher]

    def get(self, request, pk):
        submission = AssignmentSubmission.objects.filter(
            tenant=get_tenant(request),
            id=pk,
            assignment__teacher=request.user,
        ).select_related('student', 'assignment').prefetch_related(
            'answers__question', 'answers__selected_options',
            'anti_cheat_logs', 'ai_grades',
        ).first()

        if not submission:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)

        answers_data = []
        for ans in submission.answers.all():
            answers_data.append({
                'question': ans.question.question_text,
                'question_type': ans.question.question_type,
                'selected_options': [o.option_text for o in ans.selected_options.all()],
                'text_answer': ans.text_answer,
                'file_answer': ans.file_answer.url if ans.file_answer else None,
                'time_spent': ans.time_spent_seconds,
            })

        ai_grades = {}
        for grade in submission.ai_grades.all():
            key = str(grade.question_id) if grade.question_id else 'total'
            ai_grades[key] = {
                'score': float(grade.score),
                'max_score': float(grade.max_score),
                'feedback': grade.feedback,
                'rubric': grade.rubric_breakdown,
            }

        return Response({
            'success': True,
            'data': {
                'submission': SubmissionStatusSerializer(submission).data,
                'answers': answers_data,
                'ai_grades': ai_grades,
                'anti_cheat': AntiCheatLogSerializer(
                    submission.anti_cheat_logs.all(), many=True
                ).data,
            }
        })  