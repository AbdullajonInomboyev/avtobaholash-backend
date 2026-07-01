from django.urls import path
from . import views

urlpatterns = [
    path('subjects/', views.SubjectListCreateView.as_view()),
    path('subjects/<uuid:pk>/', views.SubjectDetailView.as_view()),
    path('terms/', views.AcademicTermListCreateView.as_view()),
    path('terms/<uuid:pk>/', views.AcademicTermDetailView.as_view()),
    path('assignments/', views.SubjectAssignmentListCreateView.as_view()),
    path('assignments/<uuid:pk>/', views.SubjectAssignmentDetailView.as_view()),
]
