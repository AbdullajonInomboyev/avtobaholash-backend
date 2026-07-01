from django.urls import path
from .views import SyllabusUploadView, SyllabusDetailView, SyllabusManualTopicsView

urlpatterns = [
    path('', SyllabusUploadView.as_view()),
    path('<uuid:pk>/', SyllabusDetailView.as_view()),
    path('<uuid:pk>/topics/', SyllabusManualTopicsView.as_view()),
]
