from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/exam/(?P<submission_id>[^/]+)/$', consumers.ExamConsumer.as_asgi()),
    re_path(r'ws/monitor/(?P<assignment_id>[^/]+)/$', consumers.MonitorConsumer.as_asgi()),
]
