"""
Question Bank — Savol banki
"""
from rest_framework import serializers, generics, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.urls import path

from core.permissions import IsTeacher
from .models import QuestionBank, BulkImportLog


class QuestionBankSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    topic_title = serializers.CharField(source='topic.title', read_only=True, default=None)

    class Meta:
        model = QuestionBank
        fields = [
            'id', 'subject', 'subject_name', 'topic', 'topic_title',
            'question_text', 'question_type', 'difficulty', 'tags',
            'options', 'usage_count', 'is_duplicate', 'created_at',
        ]
        read_only_fields = ['id', 'usage_count', 'is_duplicate', 'created_at']


class QuestionBankListView(generics.ListAPIView):
    serializer_class = QuestionBankSerializer
    permission_classes = [IsTeacher]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['subject', 'question_type', 'difficulty', 'is_duplicate']
    search_fields = ['question_text', 'tags']

    def get_queryset(self):
        return QuestionBank.objects.filter(
            tenant=self.request.user.tenant,
            teacher=self.request.user,
        ).select_related('subject', 'topic').order_by('-created_at')


class ImportLogListView(generics.ListAPIView):
    permission_classes = [IsTeacher]

    def get_queryset(self):
        return BulkImportLog.objects.filter(
            tenant=self.request.user.tenant,
            imported_by=self.request.user,
        ).order_by('-created_at')

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        data = list(qs.values(
            'id', 'import_type', 'total_rows', 'success_rows',
            'error_rows', 'status', 'created_at',
        ))
        return Response({'success': True, 'data': data})


urlpatterns = [
    path('', QuestionBankListView.as_view()),
    path('imports/', ImportLogListView.as_view()),
]
