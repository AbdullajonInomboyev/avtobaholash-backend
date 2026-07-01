from django.urls import path
from . import views

urlpatterns = [
    path('faculties/', views.FacultyListCreateView.as_view()),
    path('faculties/<uuid:pk>/', views.FacultyDetailView.as_view()),

    path('departments/', views.DepartmentListCreateView.as_view()),
    path('departments/<uuid:pk>/', views.DepartmentDetailView.as_view()),

    path('groups/', views.GroupListCreateView.as_view()),
    path('groups/<uuid:pk>/', views.GroupDetailView.as_view()),
    path('groups/<uuid:pk>/students/', views.GroupStudentsView.as_view()),
]
