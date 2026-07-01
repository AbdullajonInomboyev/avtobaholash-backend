from django.urls import path
from . import views

urlpatterns = [
    # O'qituvchi
    path('', views.AssignmentListCreateView.as_view()),
    path('<uuid:pk>/', views.AssignmentDetailView.as_view()),
    path('<uuid:pk>/publish/', views.AssignmentPublishView.as_view()),
    path('<uuid:pk>/export/pdf/', views.AssignmentPDFExportView.as_view()),
    path('<uuid:assignment_pk>/sections/', views.AssignmentSectionListCreateView.as_view()),
    path('<uuid:assignment_pk>/questions/', views.QuestionListCreateView.as_view()),
    path('<uuid:assignment_pk>/questions/<uuid:pk>/', views.QuestionDetailView.as_view()),

    # Talaba
    path('my/', views.StudentAssignmentListView.as_view()),
    path('my/<uuid:pk>/', views.StudentAssignmentDetailView.as_view()),
]
