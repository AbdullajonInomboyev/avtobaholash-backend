"""
Analytics — Dashboard va hisobotlar (rol bo'yicha)
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Avg, Count, Q
from django.urls import path

from core.permissions import IsAdmin, IsDepartmentHead
from core.utils import get_tenant


class AdminDashboardView(APIView):
    """Bosh admin / Admin dashboard"""
    permission_classes = [IsAdmin]

    def get(self, request):
        from apps.accounts.models import User, Role
        from apps.organization.models import Department
        from apps.assignments.models import Assignment
        from apps.submissions.models import AssignmentSubmission

        tenant = get_tenant(request)

        return Response({
            'success': True,
            'data': {
                'stats': {
                    'departments': Department.objects.filter(tenant=tenant, is_active=True).count(),
                    'users': User.objects.filter(tenant=tenant, is_active=True).count(),
                    'teachers': User.objects.filter(tenant=tenant, role=Role.TEACHER, is_active=True).count(),
                    'students': User.objects.filter(tenant=tenant, role=Role.STUDENT, is_active=True).count(),
                },
                'role_distribution': list(
                    User.objects.filter(tenant=tenant, is_active=True)
                    .values('role').annotate(count=Count('id'))
                ),
                'recent_departments': list(
                    Department.objects.filter(tenant=tenant)
                    .select_related('head')
                    .values('id', 'name', 'head__first_name', 'head__last_name', 'is_active')
                    .order_by('-created_at')[:5]
                ),
            }
        })


class DepartmentHeadDashboardView(APIView):
    """Kafedra mudiri dashboard"""
    permission_classes = [IsDepartmentHead]

    def get(self, request):
        from apps.organization.models import Department
        from apps.academics.models import SubjectAssignment
        from apps.grading.models import TeacherEvaluationLog, Gradebook
        from apps.assignments.models import Assignment

        dept = Department.objects.filter(head=request.user).first()
        if not dept:
            return Response({'success': False, 'message': 'Kafedra topilmadi'}, status=404)

        # O'qituvchi samaradorligi
        teachers_stats = []
        teacher_ids = SubjectAssignment.objects.filter(
            subject__department=dept
        ).values_list('teacher_id', flat=True).distinct()

        from apps.accounts.models import User
        for teacher in User.objects.filter(id__in=teacher_ids):
            evals = TeacherEvaluationLog.objects.filter(
                teacher=teacher,
                assignment__subject_assignment__subject__department=dept,
            )
            avg_score = evals.aggregate(avg=Avg('syllabus_match_score'))['avg']
            total = evals.count()
            out = evals.filter(topics_out_of_syllabus__gt=0).count()

            # Samaradorlik holati
            if avg_score is None:
                status_label = 'ma\'lumot yo\'q'
            elif avg_score >= 80:
                status_label = "A'lo"
            elif avg_score >= 60:
                status_label = 'Yaxshi'
            else:
                status_label = 'Past'

            teachers_stats.append({
                'teacher_id': str(teacher.id),
                'teacher_name': teacher.full_name,
                'total_assignments': total,
                'syllabus_match_avg': round(float(avg_score), 1) if avg_score else None,
                'out_of_syllabus_count': out,
                'status': status_label,
            })

        # Kafedra bo'yicha o'rtacha baho
        grade_avg = Gradebook.objects.filter(
            subject_assignment__subject__department=dept,
            is_confirmed=True,
        ).aggregate(avg=Avg('grade'))['avg']

        # Muammoli sohalar (AI insights)
        from apps.grading.models import AIGradingResult
        weak_topics = []  # Bu yerda aggregate qilish mumkin

        return Response({
            'success': True,
            'data': {
                'department': {'id': str(dept.id), 'name': dept.name},
                'grade_average': round(float(grade_avg), 2) if grade_avg else None,
                'teachers': teachers_stats,
            }
        })


class TeacherDashboardView(APIView):
    """O'qituvchi dashboard"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'teacher':
            return Response({'success': False, 'message': 'Ruxsat yo\'q'}, status=403)

        from apps.academics.models import SubjectAssignment
        from apps.assignments.models import Assignment
        from apps.submissions.models import AssignmentSubmission, SubmissionStatus
        from apps.grading.models import Gradebook

        tenant = get_tenant(request)
        assignments = Assignment.objects.filter(tenant=tenant, teacher=request.user)

        # Joriy topshiriqlar statistikasi
        active = assignments.filter(is_published=True)
        pending_grading = AssignmentSubmission.objects.filter(
            assignment__teacher=request.user,
            status=SubmissionStatus.SUBMITTED,
        ).count()

        # Fan bo'yicha o'rtacha baho
        subject_grades = list(
            Gradebook.objects.filter(
                subject_assignment__teacher=request.user,
                is_confirmed=True,
            ).values(
                'subject_assignment__subject__name'
            ).annotate(avg_grade=Avg('grade'))
            .order_by('-avg_grade')
        )

        return Response({
            'success': True,
            'data': {
                'stats': {
                    'total_assignments': assignments.count(),
                    'active_assignments': active.count(),
                    'pending_grading': pending_grading,
                },
                'subject_grades': [
                    {
                        'subject': item['subject_assignment__subject__name'],
                        'avg_grade': round(float(item['avg_grade']), 2),
                    }
                    for item in subject_grades
                ],
                'recent_assignments': list(
                    assignments.order_by('-created_at').values(
                        'id', 'title', 'assignment_type', 'is_published', 'end_datetime'
                    )[:5]
                ),
            }
        })


class StudentDashboardView(APIView):
    """Talaba dashboard — progress"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'student':
            return Response({'success': False, 'message': 'Ruxsat yo\'q'}, status=403)

        from apps.submissions.models import AssignmentSubmission, SubmissionStatus
        from apps.grading.models import Gradebook

        tenant = get_tenant(request)

        submissions = AssignmentSubmission.objects.filter(
            tenant=tenant, student=request.user
        )
        grades = Gradebook.objects.filter(
            tenant=tenant, student=request.user, is_confirmed=True
        ).select_related('subject_assignment__subject')

        avg_grade = grades.aggregate(avg=Avg('grade'))['avg']

        # Fan bo'yicha progress
        subject_progress = list(
            grades.values('subject_assignment__subject__name')
            .annotate(avg=Avg('grade'), count=Count('id'))
            .order_by('subject_assignment__subject__name')
        )

        # Kelgusi topshiriqlar
        from django.utils import timezone
        upcoming = submissions.filter(
            status=SubmissionStatus.ASSIGNED,
            assignment__end_datetime__gt=timezone.now(),
        ).select_related('assignment').order_by('assignment__end_datetime')[:5]

        return Response({
            'success': True,
            'data': {
                'stats': {
                    'total_assignments': submissions.count(),
                    'submitted': submissions.filter(status='submitted').count(),
                    'graded': submissions.filter(status='graded').count(),
                    'avg_grade': round(float(avg_grade), 2) if avg_grade else None,
                },
                'subject_progress': [
                    {
                        'subject': item['subject_assignment__subject__name'],
                        'avg_grade': round(float(item['avg']), 2),
                        'assignments_count': item['count'],
                    }
                    for item in subject_progress
                ],
                'upcoming_assignments': [
                    {
                        'id': str(s.id),
                        'title': s.assignment.title,
                        'end_datetime': s.assignment.end_datetime,
                    }
                    for s in upcoming
                ],
            }
        })


urlpatterns = [
    path('admin/', AdminDashboardView.as_view()),
    path('department-head/', DepartmentHeadDashboardView.as_view()),
    path('teacher/', TeacherDashboardView.as_view()),
    path('student/', StudentDashboardView.as_view()),
]