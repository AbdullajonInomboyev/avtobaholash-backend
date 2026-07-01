"""
Accounts Views — Auth va Foydalanuvchi boshqaruvi
"""
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from rest_framework import status, generics, filters
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django_filters.rest_framework import DjangoFilterBackend


class LoginRateThrottle(AnonRateThrottle):
    rate = '5/minute'
    scope = 'login'


class PasswordResetRateThrottle(AnonRateThrottle):
    rate = '3/minute'
    scope = 'password_reset'

from core.permissions import IsAdmin, IsDepartmentHead
from core.utils import get_tenant
from .models import PasswordResetToken
from .serializers import (
    LoginSerializer, UserListSerializer, UserDetailSerializer,
    CreateUserSerializer, UpdateUserSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, BulkImportSerializer,
)

User = get_user_model()


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Token yaratish
        refresh = RefreshToken.for_user(user)
        refresh['role'] = user.role
        refresh['tenant_id'] = str(user.tenant_id) if user.tenant_id else None

        # Oxirgi kirish vaqtini yangilash
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        return Response({
            'success': True,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': {
                'id': str(user.id),
                'full_name': user.full_name,
                'email': user.email,
                'role': user.role,
                'role_display': user.get_role_display(),
                'avatar': user.avatar.url if user.avatar else None,
                'is_inclusive': user.is_inclusive,
                'tenant_id': str(user.tenant_id) if user.tenant_id else None,
            }
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'success': True, 'message': 'Chiqish muvaffaqiyatli'})
        except TokenError:
            return Response({'success': False, 'message': 'Token yaroqsiz'}, status=400)


class RefreshTokenView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            refresh = RefreshToken(request.data.get('refresh'))
            return Response({
                'success': True,
                'access': str(refresh.access_token),
            })
        except TokenError:
            return Response(
                {'success': False, 'message': 'Refresh token yaroqsiz yoki muddati o\'tgan'},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class MeView(APIView):
    """Joriy foydalanuvchi ma'lumotlari"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserDetailSerializer(request.user)
        return Response({'success': True, 'data': serializer.data})

    def patch(self, request):
        serializer = UpdateUserSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'data': serializer.data})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Barcha sessionlarni bekor qilish (yangi paroldan keyin qayta login)
        try:
            refresh = RefreshToken(request.data.get('refresh', ''))
            refresh.blacklist()
        except Exception:
            pass

        return Response({'success': True, 'message': 'Parol muvaffaqiyatli o\'zgartirildi'})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email, is_active=True)
            # Token yaratish (1 soat amal qiladi)
            PasswordResetToken.objects.filter(user=user, is_used=False).update(is_used=True)
            reset_token = PasswordResetToken.objects.create(
                user=user,
                expires_at=timezone.now() + timedelta(hours=1),
            )
            # Email yuborish (Celery task)
            from tasks.notification_tasks import send_password_reset_email
            send_password_reset_email.delay(str(user.id), str(reset_token.token))
        except User.DoesNotExist:
            pass  # Xavfsizlik uchun — email mavjudligini bildirmaymiz

        return Response({
            'success': True,
            'message': 'Agar email ro\'yxatdan o\'tgan bo\'lsa, tiklash havolasi yuboriladi',
        })


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'success': True, 'message': 'Parol muvaffaqiyatli tiklandi'})


# ─── FOYDALANUVCHI BOSHQARUVI (Admin / Kafedra mudiri) ────────────────────────

class UserListCreateView(generics.ListCreateAPIView):
    """Foydalanuvchilar ro'yxati va yangi qo'shish"""
    permission_classes = [IsDepartmentHead]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active', 'is_inclusive']
    search_fields = ['first_name', 'last_name', 'email', 'student_id', 'employee_id']
    ordering_fields = ['last_name', 'created_at', 'role']
    ordering = ['last_name']

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.filter(tenant=get_tenant(self.request)).exclude(role='super_admin')

        # Kafedra mudiri faqat o'z kafedrasi odamlarini ko'radi
        if user.role == 'department_head':
            from apps.organization.models import Department
            dept = Department.objects.filter(head=user).first()
            if dept:
                # O'qituvchilar: ularning SubjectAssignment kafedrasi
                # Talabalar: guruhlari kafedrasi
                from django.db.models import Q
                from apps.academics.models import SubjectAssignment
                from apps.organization.models import StudentGroup
                teacher_ids = SubjectAssignment.objects.filter(
                    subject__department=dept
                ).values_list('teacher_id', flat=True)
                student_ids = StudentGroup.objects.filter(
                    group__department=dept, left_at__isnull=True
                ).values_list('student_id', flat=True)
                qs = qs.filter(Q(id__in=teacher_ids) | Q(id__in=student_ids))

        return qs.select_related('tenant')

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CreateUserSerializer
        return UserListSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {'success': True, 'data': UserDetailSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsDepartmentHead]

    def get_queryset(self):
        return User.objects.filter(tenant=self.request.user.tenant)

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UpdateUserSerializer
        return UserDetailSerializer

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        # O'chirish emas — deaktivatsiya
        user.is_active = False
        user.save(update_fields=['is_active'])
        return Response({'success': True, 'message': 'Foydalanuvchi deaktivlandi'})


class UserBulkImportView(APIView):
    """Excel orqali ko'p foydalanuvchi import"""
    permission_classes = [IsDepartmentHead]

    def post(self, request):
        serializer = BulkImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        file = serializer.validated_data['file']
        import_type = serializer.validated_data['import_type']

        # Celery task orqali async import
        from tasks.notification_tasks import process_bulk_import
        from apps.question_bank.models import BulkImportLog

        # Log yaratish
        log = BulkImportLog.objects.create(
            tenant=get_tenant(request),
            imported_by=request.user,
            import_type=import_type,
            file=file,
        )
        process_bulk_import.delay(str(log.id))

        return Response({
            'success': True,
            'message': 'Import jarayoni boshlandi',
            'import_id': str(log.id),
        }, status=status.HTTP_202_ACCEPTED)


class UserToggleActiveView(APIView):
    """Foydalanuvchini faollashtirish/bloklash"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            user = User.objects.get(id=pk, tenant=get_tenant(request))
            user.is_active = not user.is_active
            user.save(update_fields=['is_active'])
            action = 'faollashtirildi' if user.is_active else 'bloklandi'
            return Response({'success': True, 'message': f'Foydalanuvchi {action}'})
        except User.DoesNotExist:
            return Response({'success': False, 'message': 'Topilmadi'}, status=404)