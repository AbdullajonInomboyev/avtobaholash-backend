"""
Accounts Serializers — Auth va Foydalanuvchi
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, Role


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        user = authenticate(request=self.context.get('request'), email=email, password=password)

        if not user:
            raise serializers.ValidationError('Email yoki parol noto\'g\'ri')
        if not user.is_active:
            raise serializers.ValidationError('Hisobingiz bloklangan. Administratorga murojaat qiling')

        # Tenant tekshiruvi
        request = self.context.get('request')
        tenant = getattr(request, 'tenant', None)
        if tenant and user.tenant_id != tenant.id and user.role != Role.SUPER_ADMIN:
            raise serializers.ValidationError('Bu platformaga kirishga ruxsat yo\'q')

        data['user'] = user
        return data


class TokenResponseSerializer(serializers.Serializer):
    """Login muvaffaqiyatli bo'lganda qaytariladigan ma'lumot"""
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        user = obj['user']
        return {
            'id': str(user.id),
            'full_name': user.full_name,
            'email': user.email,
            'role': user.role,
            'role_display': user.get_role_display(),
            'avatar': user.avatar.url if user.avatar else None,
            'is_inclusive': user.is_inclusive,
            'tenant_id': str(user.tenant_id) if user.tenant_id else None,
        }


class UserListSerializer(serializers.ModelSerializer):
    """Ro'yxat uchun qisqa serializer"""
    full_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    department_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'phone', 'role', 'role_display',
            'is_active', 'is_inclusive', 'avatar', 'department_name',
            'employee_id', 'student_id', 'created_at',
        ]

    def get_department_name(self, obj):
        # Talabaning guruh va kafedrasi
        if obj.role == Role.STUDENT:
            sg = obj.student_groups.filter(left_at__isnull=True).select_related(
                'group__department'
            ).first()
            if sg:
                return sg.group.department.name
        return None


class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'tenant', 'first_name', 'last_name', 'middle_name',
            'email', 'phone', 'role', 'role_display', 'full_name',
            'avatar', 'is_active', 'is_inclusive',
            'employee_id', 'student_id',
            'telegram_chat_id', 'telegram_username',
            'last_login', 'created_at',
        ]
        read_only_fields = ['id', 'tenant', 'last_login', 'created_at']


class CreateUserSerializer(serializers.ModelSerializer):
    """Admin/Kafedra mudiri tomonidan foydalanuvchi yaratish"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'middle_name',
            'email', 'phone', 'role', 'password', 'password_confirm',
            'is_active', 'is_inclusive', 'employee_id', 'student_id',
        ]

    def validate(self, data):
        if data['password'] != data.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': 'Parollar mos emas'})
        return data

    def create(self, validated_data):
        request = self.context['request']
        # Tenant ni requestdan olamiz
        validated_data['tenant'] = request.user.tenant
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'middle_name',
            'phone', 'avatar', 'is_active', 'is_inclusive',
            'employee_id', 'student_id',
        ]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Eski parol noto\'g\'ri')
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Parollar mos emas'})
        return data

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        try:
            User.objects.get(email=value, is_active=True)
        except User.DoesNotExist:
            # Xavfsizlik uchun — email mavjudligini bildirmaymiz
            pass
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Parollar mos emas'})

        from .models import PasswordResetToken
        try:
            reset_token = PasswordResetToken.objects.get(
                token=data['token'],
                is_used=False,
                expires_at__gt=timezone.now(),
            )
            data['reset_token'] = reset_token
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError({'token': 'Token yaroqsiz yoki muddati o\'tgan'})

        return data

    def save(self):
        reset_token = self.validated_data['reset_token']
        user = reset_token.user
        user.set_password(self.validated_data['new_password'])
        user.save()
        reset_token.is_used = True
        reset_token.save()
        return user


class BulkImportSerializer(serializers.Serializer):
    """Excel orqali ko'p foydalanuvchi import qilish"""
    file = serializers.FileField()
    import_type = serializers.ChoiceField(choices=['students', 'teachers'])
    send_welcome_email = serializers.BooleanField(default=False)
