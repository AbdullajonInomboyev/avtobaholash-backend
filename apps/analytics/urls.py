from django.urls import path
from .views import AdminDashboardView, DepartmentHeadDashboardView, TeacherDashboardView, StudentDashboardView

urlpatterns = [
    path('admin/', AdminDashboardView.as_view()),
    path('department-head/', DepartmentHeadDashboardView.as_view()),
    path('teacher/', TeacherDashboardView.as_view()),
    path('student/', StudentDashboardView.as_view()),
]
