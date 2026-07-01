"""
Academics — Fan, Semestr, Biriktirish
"""
from rest_framework import serializers, generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsAdmin, IsDepartmentHead
from core.utils import get_tenant
from .models import Subject, AcademicTerm, SubjectAssignment


# ══════════════════════════════════════════════════════════
# SERIALIZERS
# ══════════════════════════════════════════════════════════

class SubjectSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)

    class Meta:
        model = Subject
        fields = [
            'id', 'department', 'department_name', 'name', 'code',
            'credit_hours', 'subject_type', 'description', 'is_active',
        ]
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['tenant'] = self.context['request'].user.tenant
        return super().create(validated_data)


class AcademicTermSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicTerm
        fields = ['id', 'name', 'start_date', 'end_date', 'is_current']
        read_only_fields = ['id']

    def create(self, validated_data):
        validated_data['tenant'] = self.context['request'].user.tenant
        return super().create(validated_data)


class SubjectAssignmentSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.CharField(source='teacher.full_name', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    term_name = serializers.CharField(source='term.name', read_only=True)
    has_syllabus = serializers.SerializerMethodField()

    class Meta:
        model = SubjectAssignment
        fields = [
            'id', 'subject', 'subject_name', 'teacher', 'teacher_name',
            'group', 'group_name', 'term', 'term_name', 'is_active', 'has_syllabus',
        ]
        read_only_fields = ['id']

    def get_has_syllabus(self, obj):
        return hasattr(obj, 'syllabus') and obj.syllabus is not None

    def create(self, validated_data):
        validated_data['tenant'] = self.context['request'].user.tenant
        return super().create(validated_data)


# ══════════════════════════════════════════════════════════
# VIEWS
# ══════════════════════════════════════════════════════════

class SubjectListCreateView(generics.ListCreateAPIView):
    serializer_class = SubjectSerializer
    permission_classes = [IsDepartmentHead]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'subject_type', 'is_active']
    search_fields = ['name', 'code']

    def get_queryset(self):
        qs = Subject.objects.filter(
            tenant=get_tenant(self.request)
        ).select_related('department')

        if self.request.user.role == 'department_head':
            from apps.organization.models import Department
            dept = Department.objects.filter(head=self.request.user).first()
            if dept:
                qs = qs.filter(department=dept)
        return qs.order_by('name')


class SubjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SubjectSerializer
    permission_classes = [IsDepartmentHead]

    def get_queryset(self):
        return Subject.objects.filter(tenant=get_tenant(self.request))

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'success': True})


class AcademicTermListCreateView(generics.ListCreateAPIView):
    serializer_class = AcademicTermSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return AcademicTerm.objects.filter(
            tenant=get_tenant(self.request)
        ).order_by('-start_date')


class AcademicTermDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AcademicTermSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return AcademicTerm.objects.filter(tenant=get_tenant(self.request))


class SubjectAssignmentListCreateView(generics.ListCreateAPIView):
    serializer_class = SubjectAssignmentSerializer
    permission_classes = [IsDepartmentHead]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['subject', 'teacher', 'group', 'term', 'is_active']

    def get_queryset(self):
        qs = SubjectAssignment.objects.filter(
            tenant=get_tenant(self.request)
        ).select_related('subject', 'teacher', 'group', 'term')

        user = self.request.user
        if user.role == 'teacher':
            qs = qs.filter(teacher=user)
        elif user.role == 'department_head':
            from apps.organization.models import Department
            dept = Department.objects.filter(head=user).first()
            if dept:
                qs = qs.filter(subject__department=dept)
        return qs


class SubjectAssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SubjectAssignmentSerializer
    permission_classes = [IsDepartmentHead]

    def get_queryset(self):
        return SubjectAssignment.objects.filter(tenant=get_tenant(self.request))

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'success': True})


# ── URLs ──────────────────────────────────────────────────
urlpatterns_academics = [
    ('subjects/', SubjectListCreateView),
    ('subjects/<uuid:pk>/', SubjectDetailView),
    ('terms/', AcademicTermListCreateView),
    ('terms/<uuid:pk>/', AcademicTermDetailView),
    ('assignments/', SubjectAssignmentListCreateView),
    ('assignments/<uuid:pk>/', SubjectAssignmentDetailView),
]