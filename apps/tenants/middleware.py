"""
Tenant Middleware — Har bir so'rovda tenant ni aniqlaydi
subdomain orqali: ttu.avtobaholash.uz → TTU tenant
"""
from django.utils.functional import SimpleLazyObject
from django.http import JsonResponse


def get_tenant_from_request(request):
    host = request.get_host().lower()
    # avtobaholash.uz yoki localhost — asosiy domen
    main_domains = ['avtobaholash.uz', 'localhost', '127.0.0.1']

    for domain in main_domains:
        if host == domain or host.endswith(':' + domain.split(':')[-1]):
            return None  # Super admin paneli

    # Subdomain ajratish: ttu.avtobaholash.uz → ttu
    subdomain = host.split('.')[0]
    if subdomain:
        try:
            from apps.tenants.models import Tenant
            return Tenant.objects.get(subdomain=subdomain, is_active=True)
        except Exception:
            return None
    return None


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = SimpleLazyObject(lambda: get_tenant_from_request(request))
        response = self.get_response(request)
        return response
