import logging
import json
from .localization import should_translate_request, translate_payload


class JsonLocalizationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not should_translate_request(request):
            return response

        if getattr(response, 'streaming', False):
            return response

        content_type = response.get('Content-Type', '')
        if 'application/json' not in content_type:
            return response

        try:
            if hasattr(response, 'data'):
                response.data = translate_payload(response.data)
                if hasattr(response, '_is_rendered'):
                    response._is_rendered = False
                response.render()
                return response
        except Exception:
            pass

        try:
            charset = getattr(response, 'charset', 'utf-8') or 'utf-8'
            payload = json.loads(response.content.decode(charset))
            translated = translate_payload(payload)
            response.content = json.dumps(translated, ensure_ascii=False).encode(charset)
            response['Content-Length'] = str(len(response.content))
        except Exception:
            return response

        return response

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
