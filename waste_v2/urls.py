from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WasteTaskViewSet, WasteCategoryViewSet

router = DefaultRouter()
router.register(r'tasks', WasteTaskViewSet)
router.register(r'categories', WasteCategoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
