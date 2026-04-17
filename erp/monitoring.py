from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import connections
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Production Health Check Endpoint (Phase 8).
    Checks DB and Redis connectivity.
    """
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown"
    }
    
    # 1. Check Database
    try:
        db_conn = connections['default']
        db_conn.cursor()
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Health Check - DB Error: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
        
    # 2. Check Redis
    try:
        cache.set('health_check', 'ok', timeout=1)
        if cache.get('health_check') == 'ok':
            health_status["redis"] = "connected"
        else:
            health_status["redis"] = "error"
            health_status["status"] = "unhealthy"
    except Exception as e:
        logger.error(f"Health Check - Redis Error: {e}")
        health_status["redis"] = "disconnected"
        health_status["status"] = "unhealthy"
        
    status_code = 200 if health_status["status"] == "healthy" else 503
    return Response(health_status, status=status_code)
