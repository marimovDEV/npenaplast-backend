from rest_framework import status
from rest_framework.response import Response


class NoDeleteMixin:
    """
    Prevent hard deletes from API endpoints.
    TZ requirement: business data should not be physically deleted.
    """

    def destroy(self, request, *args, **kwargs):
        return Response(
            {'error': "O'chirish taqiqlangan. Ma'lumotlarni bekor qilish yoki status orqali yopish kerak."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
