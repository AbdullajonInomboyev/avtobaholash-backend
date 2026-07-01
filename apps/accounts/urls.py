"""
Accounts URLs
"""
from django.urls import path
from . import views

urlpatterns = [
    # ─── Auth ──────────────────────────────────────────────
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('token/refresh/', views.RefreshTokenView.as_view(), name='token_refresh'),

    # ─── Joriy foydalanuvchi ───────────────────────────────
    path('me/', views.MeView.as_view(), name='me'),
    path('me/change-password/', views.ChangePasswordView.as_view(), name='change_password'),

    # ─── Parol tiklash ────────────────────────────────────
    path('password-reset/', views.PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # ─── Foydalanuvchi boshqaruvi ─────────────────────────
    path('users/', views.UserListCreateView.as_view(), name='user_list'),
    path('users/<uuid:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<uuid:pk>/toggle-active/', views.UserToggleActiveView.as_view(), name='user_toggle'),
    path('users/bulk-import/', views.UserBulkImportView.as_view(), name='user_bulk_import'),
]
