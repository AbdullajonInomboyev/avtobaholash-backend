from django.urls import path
from . import views

urlpatterns = [
    # O'qituvchi
    path('submission/<uuid:submission_pk>/', views.SubmissionGradesView.as_view()),
    path('override/<uuid:ai_grade_pk>/', views.TeacherGradeOverrideView.as_view()),
    path('gradebook/<uuid:subject_assignment_pk>/', views.GradebookListView.as_view()),
    path('gradebook/<uuid:subject_assignment_pk>/export/', views.GradebookExcelExportView.as_view()),

    # Talaba
    path('my/', views.StudentGradesView.as_view()),
    path('my/<uuid:submission_pk>/', views.StudentSubmissionResultView.as_view()),

    # Kafedra mudiri
    path('teacher-evaluations/', views.TeacherEvaluationListView.as_view()),
]
