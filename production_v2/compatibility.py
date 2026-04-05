from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.utils import timezone

from accounts.permissions import IsProductionRelated

from .models import DryingProcess

class ProductionTaskCompatibilityView(APIView):
    permission_classes = [IsProductionRelated]

    def get(self, request):
        # We'll return DryingProcess as 'production-tasks' for the Finishing page
        queryset = DryingProcess.objects.all().select_related('block_production')
        data = []
        for d in queryset:
            data.append({
                'id': d.id,
                'name': f"Form: {d.block_production.form_number}", # Matches .split(': ')[1]
                'stage': 'Armirlash', # Mock stage for frontend tabs
                'status': 'Drying' if d.end_time is None else 'Ready',
                'responsible_person_name': d.block_production.zames.operator.full_name if d.block_production.zames.operator else 'Admin Staff',
                'created_at': d.start_time,
                'is_completed': d.end_time is not None
            })
        return Response(data)

    def patch(self, request, pk=None):
        is_completed = request.data.get('is_completed')
        
        try:
            task = DryingProcess.objects.get(id=pk)
            if is_completed:
                task.end_time = timezone.now()
            else:
                task.end_time = None
            task.save()
            return Response({'status': 'updated'})
        except DryingProcess.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
