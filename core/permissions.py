"""
Rol asosidagi permission classlar
"""
from rest_framework.permissions import BasePermission


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'super_admin'


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ('super_admin', 'admin')


class IsDepartmentHead(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            'super_admin', 'admin', 'department_head'
        )


class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in (
            'super_admin', 'admin', 'department_head', 'teacher'
        )


class IsStudent(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'student'


class IsSameTenant(BasePermission):
    """Faqat o'z tenant ma'lumotlarini ko'rish"""
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'tenant_id'):
            return obj.tenant_id == request.user.tenant_id
        return True
