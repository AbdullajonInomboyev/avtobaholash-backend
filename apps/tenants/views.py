"""
Tenants — Universitet boshqaruvi (faqat Super Admin)
"""
from rest_framework import serializers, generics, filters
from rest_framework.response import Response
from django.urls import path

from core.permissions import IsSuperAdmin
from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    users_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = [
            'id', 'name', 'short_name', 'subdomain', 'logo',
            'email', 'phone', 'address', 'is_active',
            'contract_start', 'contract_end', 'max_users',
            'ai_model', 'syllabus_match_threshold', 'grading_sensitivity',
            'inclusive_education_enabled', 'voice_grading_enabled', 'auto_gradebook_enabled',
            'users_count', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_users_count(self, obj):
        return obj.users.filter(is_active=True).count()


class TenantListCreateView(generics.ListCreateAPIView):
    serializer_class = TenantSerializer
    permission_classes = [IsSuperAdmin]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'short_name', 'subdomain']

    def get_queryset(self):
        return Tenant.objects.all().order_by('name')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = serializer.save()
        return Response({'success': True, 'data': serializer.data}, status=201)


class TenantDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TenantSerializer
    permission_classes = [IsSuperAdmin]
    queryset = Tenant.objects.all()

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        obj.is_active = False
        obj.save(update_fields=['is_active'])
        return Response({'success': True})


urlpatterns = [
    path('', TenantListCreateView.as_view()),
    path('<uuid:pk>/', TenantDetailView.as_view()),
]
