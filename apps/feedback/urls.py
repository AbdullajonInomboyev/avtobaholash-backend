from django.urls import path
from .views import StudentFeedbackListCreateView, TeacherFeedbackListView, FeedbackReplyView, DepartmentFeedbackListView

urlpatterns = [
    path('my/', StudentFeedbackListCreateView.as_view()),
    path('teacher/', TeacherFeedbackListView.as_view()),
    path('<uuid:pk>/reply/', FeedbackReplyView.as_view()),
    path('department/', DepartmentFeedbackListView.as_view()),
]
