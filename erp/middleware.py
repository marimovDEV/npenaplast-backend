import logging
import json

class DebugToolbarMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with open('/tmp/all_requests.log', 'a') as f:
            f.write(f"REQ: {request.method} {request.path} from {request.META.get('REMOTE_ADDR')}\n")
            f.write(f"Headers: {dict(request.headers)}\n")
        
        response = self.get_response(request)
        
        with open('/tmp/all_requests.log', 'a') as f:
            f.write(f"RESP: {response.status_code}\n")
            if response.status_code >= 400:
                f.write(f"Error Content: {response.content.decode('utf-8')[:500]}\n")
            f.write(f"---\n")
            
        return response
