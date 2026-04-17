from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from accounts.permissions import IsAdmin
from .models import AlertRule, Alert
from .serializers import AlertRuleSerializer, AlertSerializer

class AlertRuleViewSet(viewsets.ModelViewSet):
    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['trigger_type', 'is_active']

class AlertViewSet(viewsets.ModelViewSet):
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = [IsAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_resolved', 'severity']

    @action(detail=False, methods=['get'])
    def unread(self, request):
        alerts = Alert.objects.filter(is_resolved=False)
        return Response(self.get_serializer(alerts, many=True).data)

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        if alert.is_resolved:
            return Response({'error': 'Allaqachon hal qilingan'}, status=400)
        
        alert.is_resolved = True
        alert.resolved_by = request.user
        alert.save()
        return Response(self.get_serializer(alert).data)
