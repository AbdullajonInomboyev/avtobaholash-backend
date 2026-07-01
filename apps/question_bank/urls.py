from django.urls import path
from .views import QuestionBankListView, ImportLogListView

urlpatterns = [
    path('', QuestionBankListView.as_view()),
    path('imports/', ImportLogListView.as_view()),
]
