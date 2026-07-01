from django.urls import path
from .views import TenantListCreateView, TenantDetailView

urlpatterns = [
    path('', TenantListCreateView.as_view()),
    path('<uuid:pk>/', TenantDetailView.as_view()),
]
