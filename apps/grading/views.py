from core.utils import get_tenant
"""
Grading — AI natijalar, O'qituvchi o'zgartirishi, Jurnal, Export
"""
from django.utils import timezone
from django.http import FileResponse
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response

from core.permissions import IsTeacher, IsDepartmentHead, IsStudent
from .models import AIGradingResult, TeacherGradeOverride, Gradebook, TeacherEvaluationLog


# ══════════════════════════════════════════════════════════
# SERIALIZERS
# ══════════════════════════════════════════════════════════

class AIGradingResultSerializer(serializers.ModelSerializer):
    question_text = serializers.CharField(source='question.question_text', read_only=True, default=None)
    percentage = serializers.ReadOnlyField()

    class Meta:
        model = AIGradingResult
        fields = [
            'id', 'question', 'question_text', 'score', 'max_score',
            'percentage', 'feedback', 'rubric_breakdown', 'confidence', 'graded_at',
        ]


class GradeOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherGradeOverride
        fields = ['new_score', 'reason']

    def validate_new_score(self, value):
        if value < 0:
            raise serializers.ValidationError('Ball manfiy bo\'lmasin')
        return value


class GradebookSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_id_num = serializers.CharField(source='student.student_id', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)

    class Meta:
        model = Gradebook
        fields = [
            'id', 'student', 'student_name', 'student_id_num',
            'assignment', 'assignment_title',
            'final_score', 'grade', 'is_confirmed', 'confirmed_at',
        ]


class TeacherEvalSerializer(serializers.ModelSerializer):
    """Kafedra mudiri uchun — o'qituvchiga ko'rinmaydi"""
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)

    class Meta:
        model = TeacherEvaluationLog
        fields = [
            'id', 'teacher', 'teacher_name', 'assignment', 'assignment_title',
            'syllabus_match_score', 'topics_covered', 'topics_out_of_syllabus',
            'question_quality_score', 'ai_feedback', 'evaluated_at',
        ]


# ══════════════════════════════════════════════════════════
# VIEWS
# ══════════════════════════════════════════════════════════

class SubmissionGradesView(APIView):
    """Bitta submission ning barcha AI baholash natijalari"""
    permission_classes = [IsTeacher]

    def get(self, request, submission_pk):
        grades = AIGradingResult.objects.filter(
            tenant=get_tenant(request),
            submission_id=submission_pk,
        ).select_related('question').order_by('question__order_index')

        return Response({
            'success': True,
            'data': AIGradingResultSerializer(grades, many=True).data,
        })


class TeacherGradeOverrideView(APIView):
    """O'qituvchi AI bahosini o'zgartiradi"""
    permission_classes = [IsTeacher]

    def post(self, request, ai_grade_pk):
        ai_grade = AIGradingResult.objects.filter(
            tenant=get_tenant(request),
            id=ai_grade_pk,
            submission__assignment__teacher=request.user,
        ).first()

        if not ai_grade:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)

        serializer = GradeOverrideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if ai_grade.max_score < serializer.validated_data['new_score']:
            return Response({
                'success': False,
                'message': f'Ball {ai_grade.max_score} dan oshmasin',
            }, status=400)

        # Override yaratish yoki yangilash
        override, _ = TeacherGradeOverride.objects.update_or_create(
            ai_grading=ai_grade,
            defaults={
                'tenant': request.user.tenant,
                'teacher': request.user,
                'original_score': ai_grade.score,
                'new_score': serializer.validated_data['new_score'],
                'reason': serializer.validated_data['reason'],
            }
        )

        # Gradebook ni ham yangilash
        _update_gradebook(ai_grade.submission)

        return Response({'success': True, 'message': 'Baho o\'zgartirildi'})


class GradebookListView(APIView):
    """O'qituvchi jurnali — tasdiqlash va export"""
    permission_classes = [IsTeacher]

    def get(self, request, subject_assignment_pk):
        entries = Gradebook.objects.filter(
            tenant=get_tenant(request),
            subject_assignment_id=subject_assignment_pk,
            subject_assignment__teacher=request.user,
        ).select_related('student', 'assignment').order_by('student__last_name')

        return Response({
            'success': True,
            'data': GradebookSerializer(entries, many=True).data,
        })

    def post(self, request, subject_assignment_pk):
        """Barcha baholarni bir vaqtda tasdiqlash"""
        now = timezone.now()
        updated = Gradebook.objects.filter(
            tenant=get_tenant(request),
            subject_assignment_id=subject_assignment_pk,
            subject_assignment__teacher=request.user,
            is_confirmed=False,
        ).update(
            is_confirmed=True,
            confirmed_at=now,
            confirmed_by=request.user,
        )
        return Response({
            'success': True,
            'message': f'{updated} ta baho tasdiqlandi',
        })


class GradebookExcelExportView(APIView):
    """Jurnalni Excel formatda yuklab olish"""
    permission_classes = [IsTeacher]

    def get(self, request, subject_assignment_pk):
        from apps.academics.models import SubjectAssignment
        sa = SubjectAssignment.objects.filter(
            tenant=get_tenant(request),
            id=subject_assignment_pk,
            teacher=request.user,
        ).select_related('subject', 'group').first()

        if not sa:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)

        entries = Gradebook.objects.filter(
            tenant=get_tenant(request),
            subject_assignment=sa,
        ).select_related('student', 'assignment').order_by('student__last_name')

        from services.export.excel import GradebookExcelExporter
        exporter = GradebookExcelExporter(sa, entries)
        excel_buffer = exporter.generate()

        filename = f'Jurnal_{sa.subject.name}_{sa.group.name}.xlsx'
        return FileResponse(excel_buffer, as_attachment=True, filename=filename)


# ── Talaba uchun natijalar ────────────────────────────────

class StudentGradesView(APIView):
    """Talabaning o'z baholarini ko'rishi"""
    permission_classes = [IsStudent]

    def get(self, request):
        grades = Gradebook.objects.filter(
            tenant=get_tenant(request),
            student=request.user,
            is_confirmed=True,
        ).select_related(
            'subject_assignment__subject',
            'assignment',
        ).order_by('-created_at')

        data = []
        for g in grades:
            # AI feedback ni olish
            ai_feedback = AIGradingResult.objects.filter(
                submission__assignment=g.assignment,
                submission__student=request.user,
                question=None,
            ).first()

            data.append({
                'assignment_id': str(g.assignment.id),
                'assignment_title': g.assignment.title,
                'subject': g.subject_assignment.subject.name,
                'final_score': float(g.final_score),
                'grade': g.grade,
                'ai_feedback': ai_feedback.feedback if ai_feedback else None,
                'confirmed_at': g.confirmed_at,
            })

        return Response({'success': True, 'data': data})


class StudentSubmissionResultView(APIView):
    """Talabaning bitta topshiriq natijasi (batafsil)"""
    permission_classes = [IsStudent]

    def get(self, request, submission_pk):
        from apps.submissions.models import AssignmentSubmission
        submission = AssignmentSubmission.objects.filter(
            tenant=get_tenant(request),
            id=submission_pk,
            student=request.user,
            status='graded',
        ).first()

        if not submission:
            return Response({'success': False, 'message': 'Natija hali tayyor emas'}, status=404)

        grades = AIGradingResult.objects.filter(
            submission=submission
        ).select_related('question')

        gradebook = Gradebook.objects.filter(
            assignment=submission.assignment,
            student=request.user,
        ).first()

        return Response({
            'success': True,
            'data': {
                'submission_id': str(submission.id),
                'assignment_title': submission.assignment.title,
                'grade': gradebook.grade if gradebook else None,
                'details': AIGradingResultSerializer(grades, many=True).data,
            }
        })


# ── Kafedra mudiri uchun ─────────────────────────────────

class TeacherEvaluationListView(APIView):
    """Kafedra mudiri — o'qituvchilar baholash jurnali"""
    permission_classes = [IsDepartmentHead]

    def get(self, request):
        from apps.organization.models import Department
        dept = Department.objects.filter(head=request.user).first()
        if not dept:
            return Response({'success': False, 'message': 'Kafedra topilmadi'}, status=404)

        evals = TeacherEvaluationLog.objects.filter(
            tenant=get_tenant(request),
            assignment__subject_assignment__subject__department=dept,
        ).select_related('teacher', 'assignment').order_by('-evaluated_at')

        # Filter
        teacher_id = request.query_params.get('teacher_id')
        if teacher_id:
            evals = evals.filter(teacher_id=teacher_id)

        return Response({
            'success': True,
            'data': TeacherEvalSerializer(evals, many=True).data,
        })


# ── Yordamchi ────────────────────────────────────────────

def _update_gradebook(submission):
    """AI override dan keyin gradebook ni yangilaydi"""
    from decimal import Decimal
    total = AIGradingResult.objects.filter(
        submission=submission, question=None
    ).first()
    if not total:
        return

    # Override tekshirish
    final_score = total.score
    try:
        final_score = total.teacher_override.new_score
    except TeacherGradeOverride.DoesNotExist:
        pass

    def score_to_grade(score, max_score):
        if max_score == 0:
            return 2
        pct = float(score) / float(max_score) * 100
        if pct >= 86:
            return 5
        elif pct >= 71:
            return 4
        elif pct >= 56:
            return 3
        return 2

    Gradebook.objects.filter(
        assignment=submission.assignment,
        student=submission.student,
    ).update(
        final_score=final_score,
        grade=score_to_grade(final_score, total.max_score),
    )