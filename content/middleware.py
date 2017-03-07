

class UTMMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.session.get('utm', None) is None:
            request.session['utm'] = request.build_absolute_uri()
        return self.get_response(request)