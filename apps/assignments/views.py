from core.utils import get_tenant
"""
Assignments — Topshiriq yaratish, savollar, yuborish, PDF export
"""
import io
from django.http import FileResponse
from django.utils import timezone
from rest_framework import serializers, generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsTeacher, IsDepartmentHead, IsStudent
from .models import Assignment, AssignmentSection, Question, AnswerOption


# ══════════════════════════════════════════════════════════
# SERIALIZERS
# ══════════════════════════════════════════════════════════

class AnswerOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerOption
        fields = ['id', 'option_text', 'is_correct', 'order_index']
        read_only_fields = ['id']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Talabaga to'g'ri javobni ko'rsatmaymiz
        request = self.context.get('request')
        if request and request.user.role == 'student':
            data.pop('is_correct', None)
        return data


class QuestionSerializer(serializers.ModelSerializer):
    options = AnswerOptionSerializer(many=True, required=False)

    class Meta:
        model = Question
        fields = [
            'id', 'section', 'question_text', 'question_type',
            'points', 'order_index', 'media', 'options',
            'is_tts_readable', 'tts_text',
        ]
        read_only_fields = ['id', 'is_tts_readable', 'tts_text']

    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        question = Question.objects.create(**validated_data)
        for opt in options_data:
            AnswerOption.objects.create(
                tenant=question.tenant,
                question=question,
                **opt,
            )
        return question


class AssignmentSectionSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = AssignmentSection
        fields = ['id', 'title', 'topic', 'questions_count', 'order_index', 'questions']
        read_only_fields = ['id']


class AssignmentListSerializer(serializers.ModelSerializer):
    """Ro'yxat uchun qisqa"""
    subject_name = serializers.CharField(source='subject_assignment.subject.name', read_only=True)
    group_name = serializers.CharField(source='subject_assignment.group.name', read_only=True)
    questions_count = serializers.SerializerMethodField()
    submissions_count = serializers.SerializerMethodField()
    ai_relevance_score = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            'id', 'title', 'assignment_type', 'subject_name', 'group_name',
            'start_datetime', 'end_datetime', 'duration_minutes',
            'is_published', 'questions_count', 'submissions_count', 'ai_relevance_score',
        ]

    def get_questions_count(self, obj):
        return obj.questions.count()

    def get_submissions_count(self, obj):
        return obj.submissions.count()

    def get_ai_relevance_score(self, obj):
        # Faqat kafedra mudiri va adminga ko'rinadi
        request = self.context.get('request')
        if request and request.user.role in ('department_head', 'admin', 'super_admin'):
            return obj.ai_relevance_score
        return None


class AssignmentDetailSerializer(serializers.ModelSerializer):
    sections = AssignmentSectionSerializer(many=True, read_only=True)
    questions = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            'id', 'subject_assignment', 'title', 'description', 'assignment_type',
            'duration_minutes', 'start_datetime', 'end_datetime',
            'total_questions', 'shuffle_questions', 'show_result_immediately',
            'allowed_file_types', 'max_file_size_mb', 'is_inclusive', 'is_published',
            'sections', 'questions',
        ]
        read_only_fields = ['id']

    def get_questions(self, obj):
        # Sections bo'lmasa — barcha savollar
        if obj.sections.exists():
            return []
        qs = obj.questions.prefetch_related('options')
        return QuestionSerializer(qs, many=True, context=self.context).data


class AssignmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = [
            'subject_assignment', 'title', 'description', 'assignment_type',
            'duration_minutes', 'start_datetime', 'end_datetime',
            'total_questions', 'shuffle_questions', 'show_result_immediately',
            'allowed_file_types', 'max_file_size_mb', 'is_inclusive',
        ]

    def create(self, validated_data):
        request = self.context['request']
        validated_data['tenant'] = request.user.tenant
        validated_data['teacher'] = request.user
        return super().create(validated_data)


# ══════════════════════════════════════════════════════════
# VIEWS
# ══════════════════════════════════════════════════════════

class AssignmentListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['assignment_type', 'is_published', 'subject_assignment']
    search_fields = ['title']

    def get_serializer_class(self):
        return AssignmentCreateSerializer if self.request.method == 'POST' else AssignmentListSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Assignment.objects.filter(tenant=get_tenant(self.request))
        if user.role == 'teacher':
            qs = qs.filter(teacher=user)
        elif user.role == 'department_head':
            from apps.organization.models import Department
            dept = Department.objects.filter(head=user).first()
            if dept:
                qs = qs.filter(subject_assignment__subject__department=dept)
        return qs.select_related('subject_assignment__subject', 'subject_assignment__group')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        return Response(
            {'success': True, 'data': AssignmentDetailSerializer(assignment, context={'request': request}).data},
            status=status.HTTP_201_CREATED,
        )


class AssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsTeacher]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return AssignmentCreateSerializer
        return AssignmentDetailSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Assignment.objects.filter(tenant=get_tenant(self.request))
        # O'qituvchi faqat o'z topshiriqlarini o'zgartira oladi
        if user.role == 'teacher':
            qs = qs.filter(teacher=user)
        return qs


class AssignmentPublishView(APIView):
    """Topshiriqni nashr qilish — barcha talablarga yuborish"""
    permission_classes = [IsTeacher]

    def post(self, request, pk):
        assignment = Assignment.objects.filter(
            tenant=get_tenant(request), id=pk, teacher=request.user
        ).first()
        if not assignment:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)
        if assignment.is_published:
            return Response({'success': False, 'message': 'Allaqachon nashr qilingan'}, status=400)

        assignment.is_published = True
        assignment.save(update_fields=['is_published'])

        # Async: talablarga yuborish + AI tekshiruv + TTS
        from tasks.notification_tasks import send_assignment_notifications
        from tasks.ai_tasks import ai_check_assignment_relevance, ai_process_tts
        send_assignment_notifications.delay(str(assignment.id))
        ai_check_assignment_relevance.delay(str(assignment.id))
        if assignment.is_inclusive:
            ai_process_tts.delay(str(assignment.id))

        return Response({'success': True, 'message': 'Topshiriq nashr qilindi va talablarga yuborildi'})


class QuestionListCreateView(APIView):
    """Topshiriqqa savol qo'shish"""
    permission_classes = [IsTeacher]

    def get(self, request, assignment_pk):
        questions = Question.objects.filter(
            tenant=get_tenant(request),
            assignment_id=assignment_pk,
        ).prefetch_related('options', 'section').order_by('order_index')
        return Response({
            'success': True,
            'data': QuestionSerializer(questions, many=True, context={'request': request}).data,
        })

    def post(self, request, assignment_pk):
        assignment = Assignment.objects.filter(
            tenant=get_tenant(request), id=assignment_pk, teacher=request.user
        ).first()
        if not assignment:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)

        # Ko'p savol bir vaqtda yuklash (bulk)
        is_bulk = isinstance(request.data, list)
        data = request.data if is_bulk else [request.data]

        created = []
        for item in data:
            item['assignment'] = str(assignment_pk)
            serializer = QuestionSerializer(data=item, context={'request': request})
            serializer.is_valid(raise_exception=True)
            q = serializer.save(
                tenant=assignment.tenant,
                assignment=assignment,
            )
            created.append(q)

        # Savol bankiga ham qo'shish
        _save_to_question_bank(created, assignment, request.user)

        return Response({
            'success': True,
            'message': f'{len(created)} ta savol qo\'shildi',
            'data': QuestionSerializer(created, many=True, context={'request': request}).data,
        }, status=status.HTTP_201_CREATED)


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = QuestionSerializer
    permission_classes = [IsTeacher]

    def get_queryset(self):
        return Question.objects.filter(
            tenant=get_tenant(self.request),
            assignment__teacher=self.request.user,
        )


class AssignmentSectionListCreateView(APIView):
    """Bo'lim (section) boshqaruvi"""
    permission_classes = [IsTeacher]

    def get(self, request, assignment_pk):
        sections = AssignmentSection.objects.filter(
            tenant=get_tenant(request),
            assignment_id=assignment_pk,
        ).prefetch_related('questions__options')
        return Response({
            'success': True,
            'data': AssignmentSectionSerializer(sections, many=True).data,
        })

    def post(self, request, assignment_pk):
        assignment = Assignment.objects.filter(
            tenant=get_tenant(request), id=assignment_pk, teacher=request.user
        ).first()
        if not assignment:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)
        serializer = AssignmentSectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        section = serializer.save(tenant=assignment.tenant, assignment=assignment)
        return Response({'success': True, 'data': AssignmentSectionSerializer(section).data},
                        status=status.HTTP_201_CREATED)


class AssignmentPDFExportView(APIView):
    """Topshiriqni PDF formatda yuklab olish (offline tarqatish uchun)"""
    permission_classes = [IsTeacher]

    def get(self, request, pk):
        assignment = Assignment.objects.filter(
            tenant=get_tenant(request), id=pk
        ).prefetch_related('questions__options', 'sections').first()
        if not assignment:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)

        from services.export.pdf import AssignmentPDFExporter
        exporter = AssignmentPDFExporter(assignment)
        pdf_buffer = exporter.generate()

        filename = f'{assignment.title[:50]}.pdf'
        return FileResponse(pdf_buffer, as_attachment=True, filename=filename)


# ── Student uchun topshiriqlar ────────────────────────────

class StudentAssignmentListView(APIView):
    """Talabaning topshiriqlari"""
    permission_classes = [IsStudent]

    def get(self, request):
        from apps.submissions.models import AssignmentSubmission
        submissions = AssignmentSubmission.objects.filter(
            tenant=get_tenant(request),
            student=request.user,
        ).select_related(
            'assignment__subject_assignment__subject',
            'assignment__teacher',
        ).order_by('assignment__end_datetime')

        data = []
        for sub in submissions:
            a = sub.assignment
            data.append({
                'submission_id': str(sub.id),
                'assignment_id': str(a.id),
                'title': a.title,
                'type': a.assignment_type,
                'subject': a.subject_assignment.subject.name,
                'teacher': a.teacher.full_name,
                'start_datetime': a.start_datetime,
                'end_datetime': a.end_datetime,
                'duration_minutes': a.duration_minutes,
                'status': sub.status,
                'is_locked': sub.is_locked,
            })

        return Response({'success': True, 'data': data})


class StudentAssignmentDetailView(APIView):
    """Talabaga topshiriq tafsilotlari — imtihon boshlashdan oldin"""
    permission_classes = [IsStudent]

    def get(self, request, pk):
        from apps.submissions.models import AssignmentSubmission, SubmissionStatus
        submission = AssignmentSubmission.objects.filter(
            tenant=get_tenant(request),
            student=request.user,
            assignment_id=pk,
        ).select_related('assignment').first()

        if not submission:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)
        if submission.is_locked:
            return Response({'success': False, 'message': f'Bloklangan: {submission.lock_reason}'}, status=403)

        assignment = submission.assignment
        now = timezone.now()

        if now < assignment.start_datetime:
            return Response({'success': False, 'message': 'Topshiriq hali boshlanmagan'}, status=400)
        if now > assignment.end_datetime:
            if submission.status == SubmissionStatus.ASSIGNED:
                submission.status = SubmissionStatus.EXPIRED
                submission.save(update_fields=['status'])
            return Response({'success': False, 'message': 'Topshiriq muddati o\'tgan'}, status=400)

        # Boshlash
        if submission.status == SubmissionStatus.ASSIGNED:
            submission.status = SubmissionStatus.STARTED
            submission.started_at = now
            submission.ip_address = request.META.get('REMOTE_ADDR')
            submission.save(update_fields=['status', 'started_at', 'ip_address'])

        # Savollarni deterministik aralashtirish (submission ga bog'liq)
        questions = _get_shuffled_questions(assignment, submission)

        return Response({
            'success': True,
            'data': {
                'submission_id': str(submission.id),
                'assignment': AssignmentDetailSerializer(assignment, context={'request': request}).data,
                'questions': QuestionSerializer(questions, many=True, context={'request': request}).data,
                'time_remaining_seconds': int((assignment.end_datetime - now).total_seconds()),
            }
        })


# ── Yordamchi funksiyalar ─────────────────────────────────

def _get_shuffled_questions(assignment, submission):
    """
    Bo'limlar bo'yicha random savollarni tanlaydi.
    Tartib submission ga bog'liq — har safar bir xil natija.
    """
    import random
    import hashlib

    # Submission ID dan deterministik seed yaratamiz
    # Bir xil submission uchun har doim bir xil tartib
    seed = int(hashlib.md5(str(submission.id).encode()).hexdigest(), 16) % (2**31)
    rng = random.Random(seed)

    questions = []
    sections = assignment.sections.prefetch_related('questions__options')

    if sections.exists():
        for section in sections:
            qs = list(section.questions.all())
            count = min(section.questions_count, len(qs))
            questions.extend(rng.sample(qs, count))
    else:
        qs = list(assignment.questions.prefetch_related('options'))
        if assignment.shuffle_questions:
            rng.shuffle(qs)
        questions = qs

    return questions


def _save_to_question_bank(questions, assignment, teacher):
    """Yangi savollarni savol bankiga ham saqlaydi"""
    from apps.question_bank.models import QuestionBank
    for q in questions:
        options = [
            {'text': o.option_text, 'is_correct': o.is_correct}
            for o in q.options.all()
        ]
        QuestionBank.objects.get_or_create(
            tenant=q.tenant,
            teacher=teacher,
            subject=assignment.subject_assignment.subject,
            question_text=q.question_text,
            defaults={
                'question_type': q.question_type,
                'options': options,
            }
        )