from desw.server import app


_gunicorn_app = None


def gunicorn_app(environ, start_response):
    global _gunicorn_app
    if _gunicorn_app is None:
        _gunicorn_app = app
    return _gunicorn_app(environ, start_response)
