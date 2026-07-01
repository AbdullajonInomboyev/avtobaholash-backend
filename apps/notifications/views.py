from core.utils import get_tenant
"""
Notifications — Bildirishnomalar
"""
from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.urls import path

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'body', 'notification_type', 'link', 'is_read', 'sent_at', 'read_at']


class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(
            tenant=get_tenant(request),
            recipient=request.user,
        ).order_by('-sent_at')[:50]

        unread_count = Notification.objects.filter(
            tenant=get_tenant(request),
            recipient=request.user,
            is_read=False,
        ).count()

        return Response({
            'success': True,
            'unread_count': unread_count,
            'data': NotificationSerializer(notifications, many=True).data,
        })


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Barchasini o'qildi deb belgilash"""
        from django.utils import timezone
        Notification.objects.filter(
            tenant=get_tenant(request),
            recipient=request.user,
            is_read=False,
        ).update(is_read=True, read_at=timezone.now())
        return Response({'success': True})

    def patch(self, request, pk):
        """Bittasini o'qildi deb belgilash"""
        from django.utils import timezone
        Notification.objects.filter(
            tenant=get_tenant(request),
            recipient=request.user,
            id=pk,
        ).update(is_read=True, read_at=timezone.now())
        return Response({'success': True})


urlpatterns = [
    path('', NotificationListView.as_view()),
    path('mark-read/', NotificationMarkReadView.as_view()),
    path('<uuid:pk>/mark-read/', NotificationMarkReadView.as_view()),
]