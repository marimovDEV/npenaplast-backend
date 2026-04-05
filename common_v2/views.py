from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import AuditLog, Notification
from .serializers import AuditLogSerializer, NotificationSerializer
from accounts.models import User
from accounts.permissions import IsAdmin

class NotificationViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'All notifications marked as read'})

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'Notification marked as read'})

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.full_name')

    class Meta:
        model = AuditLog
        fields = '__all__'

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    filterset_fields = {
        'module': ['exact', 'icontains'],
        'action': ['exact'],
        'user': ['exact'],
        'status': ['exact'],
        'timestamp': ['gte', 'lte'],
    }
    search_fields = ['description', 'ip_address', 'module']
    ordering_fields = ['timestamp', 'user_name']
    ordering = ['-timestamp']

    @action(detail=False, methods=['get'])
    def active_users(self, request):
        ten_mins_ago = timezone.now() - timedelta(minutes=10)
        active_count = User.objects.filter(last_login__gte=ten_mins_ago).count()
        
        # Also count users who had audit log entries recently
        audit_users = AuditLog.objects.filter(timestamp__gte=ten_mins_ago).values_list('user', flat=True).distinct()
        audit_count = len([u for u in audit_users if u is not None])
        
        total_active = max(active_count, audit_count)
        total_users = User.objects.count()
        
        return Response({
            'active_count': total_active,
            'total_users': total_users,
            'status': 'Stable'
        })
