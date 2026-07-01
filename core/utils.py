"""
Yordamchi funksiyalar
"""

def get_tenant(request):
    """
    Super admin uchun birinchi tenant ni qaytaradi.
    Boshqa rollar uchun o'z tenant ini qaytaradi.
    """
    user = request.user
    if user.role == 'super_admin' and not user.tenant:
        from apps.tenants.models import Tenant
        return Tenant.objects.first()
    return user.tenant