from django.urls import path
from . import views

urlpatterns = [
    # Talaba
    path('<uuid:submission_pk>/answer/', views.SubmitAnswerView.as_view()),
    path('<uuid:submission_pk>/answer/file/', views.SubmitFileAnswerView.as_view()),
    path('<uuid:submission_pk>/submit/', views.FinalSubmitView.as_view()),
    path('<uuid:submission_pk>/anti-cheat/', views.AntiCheatEventView.as_view()),

    # O'qituvchi
    path('assignment/<uuid:assignment_pk>/', views.TeacherSubmissionsView.as_view()),
    path('<uuid:pk>/detail/', views.SubmissionDetailView.as_view()),
]
