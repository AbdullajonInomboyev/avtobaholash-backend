"""
Organization — Serializers, Views, URLs
"""
from rest_framework import serializers, generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from core.permissions import IsAdmin, IsDepartmentHead
from core.utils import get_tenant
from .models import Faculty, Department, Group, StudentGroup


# ══════════════════════════════════════════════════════════
# SERIALIZERS
# ══════════════════════════════════════════════════════════

class FacultySerializer(serializers.ModelSerializer):
    dean_name = serializers.CharField(source='dean.full_name', read_only=True, default=None)
    departments_count = serializers.SerializerMethodField()

    class Meta:
        model = Faculty
        fields = ['id', 'name', 'code', 'dean', 'dean_name', 'departments_count', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_departments_count(self, obj):
        return obj.departments.filter(is_active=True).count()

    def create(self, validated_data):
        validated_data['tenant'] = get_tenant(self.context['request'])
        return super().create(validated_data)


class DepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.CharField(source='head.full_name', read_only=True, default=None)
    faculty_name = serializers.CharField(source='faculty.name', read_only=True, default=None)
    teachers_count = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id', 'faculty', 'faculty_name', 'name', 'code',
            'head', 'head_name', 'teachers_count', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_teachers_count(self, obj):
        from apps.academics.models import SubjectAssignment
        return SubjectAssignment.objects.filter(
            subject__department=obj
        ).values('teacher').distinct().count()

    def create(self, validated_data):
        validated_data['tenant'] = get_tenant(self.context['request'])
        return super().create(validated_data)


class GroupSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    students_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            'id', 'department', 'department_name', 'name',
            'year', 'education_form', 'students_count', 'is_active',
        ]
        read_only_fields = ['id']

    def get_students_count(self, obj):
        return obj.student_memberships.filter(left_at__isnull=True).count()

    def create(self, validated_data):
        validated_data['tenant'] = get_tenant(self.context['request'])
        return super().create(validated_data)


class StudentGroupSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)

    class Meta:
        model = StudentGroup
        fields = ['id', 'student', 'student_name', 'student_email', 'group', 'joined_at', 'left_at']
        read_only_fields = ['id', 'joined_at']


# ══════════════════════════════════════════════════════════
# VIEWS
# ══════════════════════════════════════════════════════════

class FacultyListCreateView(generics.ListCreateAPIView):
    serializer_class = FacultySerializer
    permission_classes = [IsAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'code']

    def get_queryset(self):
        tenant = get_tenant(self.request)
        return Faculty.objects.filter(tenant=tenant).select_related('dean').order_by('name')


class FacultyDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = FacultySerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return Faculty.objects.filter(tenant=get_tenant(self.request))

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'success': True})


class DepartmentListCreateView(generics.ListCreateAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [IsDepartmentHead]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['faculty', 'is_active']
    search_fields = ['name', 'code']

    def get_queryset(self):
        tenant = get_tenant(self.request)
        qs = Department.objects.filter(tenant=tenant).select_related('faculty', 'head').order_by('name')
        if self.request.user.role == 'department_head':
            dept = Department.objects.filter(head=self.request.user).first()
            if dept:
                qs = qs.filter(id=dept.id)
        return qs


class DepartmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DepartmentSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return Department.objects.filter(tenant=get_tenant(self.request))

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'success': True})


class GroupListCreateView(generics.ListCreateAPIView):
    serializer_class = GroupSerializer
    permission_classes = [IsDepartmentHead]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['department', 'year', 'education_form', 'is_active']
    search_fields = ['name']

    def get_queryset(self):
        tenant = get_tenant(self.request)
        qs = Group.objects.filter(tenant=tenant).select_related('department')
        if self.request.user.role == 'department_head':
            dept = Department.objects.filter(head=self.request.user).first()
            if dept:
                qs = qs.filter(department=dept)
        return qs.order_by('name')


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GroupSerializer
    permission_classes = [IsDepartmentHead]

    def get_queryset(self):
        return Group.objects.filter(tenant=get_tenant(self.request))

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'success': True})


class GroupStudentsView(APIView):
    permission_classes = [IsDepartmentHead]

    def get(self, request, pk):
        tenant = get_tenant(request)
        group = Group.objects.filter(tenant=tenant, id=pk).first()
        if not group:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)
        memberships = StudentGroup.objects.filter(
            group=group, left_at__isnull=True
        ).select_related('student')
        serializer = StudentGroupSerializer(memberships, many=True)
        return Response({'success': True, 'data': serializer.data})

    def post(self, request, pk):
        tenant = get_tenant(request)
        group = Group.objects.filter(tenant=tenant, id=pk).first()
        if not group:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)
        student_ids = request.data.get('student_ids', [])
        added = 0
        for sid in student_ids:
            obj, created = StudentGroup.objects.get_or_create(
                tenant=tenant, student_id=sid, group=group,
                defaults={'left_at': None},
            )
            if not created and obj.left_at:
                obj.left_at = None
                obj.save(update_fields=['left_at'])
                created = True
            if created:
                added += 1
        return Response({'success': True, 'message': f'{added} ta talaba qo\'shildi'})

    def delete(self, request, pk):
        from django.utils import timezone
        tenant = get_tenant(request)
        group = Group.objects.filter(tenant=tenant, id=pk).first()
        if not group:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)
        student_id = request.data.get('student_id')
        StudentGroup.objects.filter(
            group=group, student_id=student_id, left_at__isnull=True
        ).update(left_at=timezone.now().date())
        return Response({'success': True, 'message': 'Talaba guruhdan chiqarildi'})