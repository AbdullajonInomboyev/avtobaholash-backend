from core.utils import get_tenant
"""
Syllabus — Sillabus yuklash, mavzular, AI qayta ishlash
"""
from rest_framework import serializers, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser

from core.permissions import IsTeacher, IsDepartmentHead
from .models import Syllabus, SyllabusTopic


# ══════════════════════════════════════════════════════════
# SERIALIZERS
# ══════════════════════════════════════════════════════════

class SyllabusTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = SyllabusTopic
        fields = ['id', 'topic_number', 'title', 'description', 'week_number', 'hours']
        read_only_fields = ['id']


class SyllabusSerializer(serializers.ModelSerializer):
    topics = SyllabusTopicSerializer(many=True, read_only=True)
    topics_count = serializers.SerializerMethodField()

    class Meta:
        model = Syllabus
        fields = [
            'id', 'subject_assignment', 'file', 'file_type',
            'ai_processed', 'ai_processed_at', 'topics_count', 'topics', 'created_at',
        ]
        read_only_fields = ['id', 'ai_processed', 'ai_processed_at', 'file_type', 'created_at']

    def get_topics_count(self, obj):
        return obj.topics.count()


class SyllabusUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Syllabus
        fields = ['subject_assignment', 'file']

    def validate_file(self, value):
        allowed = ['pdf', 'docx', 'doc', 'txt']
        ext = value.name.split('.')[-1].lower()
        if ext not in allowed:
            raise serializers.ValidationError(f'Faqat {", ".join(allowed)} formatlarga ruxsat')
        if value.size > 10 * 1024 * 1024:  # 10MB
            raise serializers.ValidationError('Fayl hajmi 10MB dan oshmasin')
        return value

    def create(self, validated_data):
        file = validated_data['file']
        validated_data['file_type'] = file.name.split('.')[-1].lower()
        validated_data['tenant'] = self.context['request'].user.tenant
        # Eski sillabusni o'chirish
        Syllabus.objects.filter(
            subject_assignment=validated_data['subject_assignment']
        ).delete()
        return super().create(validated_data)


class ManualTopicSerializer(serializers.ModelSerializer):
    """O'qituvchi qo'lda mavzu kiritishi uchun"""
    class Meta:
        model = SyllabusTopic
        fields = ['topic_number', 'title', 'description', 'week_number', 'hours']


# ══════════════════════════════════════════════════════════
# VIEWS
# ══════════════════════════════════════════════════════════

class SyllabusUploadView(APIView):
    """Sillabus fayl yuklash — AI avtomatik mavzularni ajratadi"""
    permission_classes = [IsTeacher]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        """O'qituvchining barcha sillabuslari"""
        syllabuses = Syllabus.objects.filter(
            tenant=get_tenant(request),
            subject_assignment__teacher=request.user,
        ).select_related('subject_assignment__subject')
        serializer = SyllabusSerializer(syllabuses, many=True)
        return Response({'success': True, 'data': serializer.data})

    def post(self, request):
        serializer = SyllabusUploadSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        syllabus = serializer.save()

        # AI mavzularni ajratadi (async)
        from tasks.ai_tasks import ai_process_syllabus
        ai_process_syllabus.delay(str(syllabus.id))

        return Response({
            'success': True,
            'message': 'Sillabus yuklandi. AI mavzularni ajratmoqda...',
            'data': SyllabusSerializer(syllabus).data,
        }, status=status.HTTP_201_CREATED)


class SyllabusDetailView(APIView):
    permission_classes = [IsTeacher]

    def get(self, request, pk):
        syllabus = Syllabus.objects.filter(
            tenant=get_tenant(request), id=pk
        ).select_related('subject_assignment').prefetch_related('topics').first()
        if not syllabus:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)
        return Response({'success': True, 'data': SyllabusSerializer(syllabus).data})

    def delete(self, request, pk):
        deleted, _ = Syllabus.objects.filter(
            tenant=get_tenant(request), id=pk,
            subject_assignment__teacher=request.user,
        ).delete()
        if not deleted:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)
        return Response({'success': True})


class SyllabusManualTopicsView(APIView):
    """Sillabus fayli bo'lmasa — qo'lda mavzu kiritish"""
    permission_classes = [IsTeacher]

    def post(self, request, pk):
        syllabus = Syllabus.objects.filter(
            tenant=get_tenant(request), id=pk,
            subject_assignment__teacher=request.user,
        ).first()
        if not syllabus:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)

        topics_data = request.data.get('topics', [])
        if not topics_data:
            return Response({'success': False, 'message': 'Mavzular bo\'sh'}, status=400)

        serializer = ManualTopicSerializer(data=topics_data, many=True)
        serializer.is_valid(raise_exception=True)

        # Eski mavzularni o'chirish
        SyllabusTopic.objects.filter(syllabus=syllabus).delete()

        # Yangilarini qo'shish
        topics = [
            SyllabusTopic(
                tenant=get_tenant(request),
                syllabus=syllabus,
                **topic,
            )
            for topic in serializer.validated_data
        ]
        SyllabusTopic.objects.bulk_create(topics)

        syllabus.ai_processed = True
        syllabus.save(update_fields=['ai_processed'])

        return Response({
            'success': True,
            'message': f'{len(topics)} ta mavzu saqlandi',
            'data': SyllabusTopicSerializer(topics, many=True).data,
        })


# ── URLs ──────────────────────────────────────────────────
from django.urls import path

urlpatterns = [
    path('', SyllabusUploadView.as_view()),
    path('<uuid:pk>/', SyllabusDetailView.as_view()),
    path('<uuid:pk>/topics/', SyllabusManualTopicsView.as_view()),
]