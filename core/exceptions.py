"""
Barcha API xatolar uchun yagona format
"""
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        error_data = {
            'success': False,
            'status_code': response.status_code,
            'errors': response.data,
        }

        # Xato turini aniqlashtirish
        if response.status_code == 401:
            error_data['message'] = 'Autentifikatsiya talab etiladi'
        elif response.status_code == 403:
            error_data['message'] = 'Ruxsat yo\'q'
        elif response.status_code == 404:
            error_data['message'] = 'Topilmadi'
        elif response.status_code == 429:
            error_data['message'] = 'So\'rovlar soni oshib ketdi, biroz kuting'
        else:
            error_data['message'] = 'Xato yuz berdi'

        response.data = error_data

    return response
