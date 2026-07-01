from django.urls import path
from .views import NotificationListView, NotificationMarkReadView

urlpatterns = [
    path('', NotificationListView.as_view()),
    path('mark-read/', NotificationMarkReadView.as_view()),
    path('<uuid:pk>/mark-read/', NotificationMarkReadView.as_view()),
]
