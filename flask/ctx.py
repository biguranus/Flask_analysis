'''Created on 2018年3月23日@author: litian'''
import sys


class RequestContext(object):
    """The request context contains all request relevant information.  It is
    created at the beginning of the request and pushed to the
    `_request_ctx_stack` and removed at the end of it.  It will create the
    URL adapter and request object for the WSGI environment provided.
    """
    
    def __init__(self, app, environ, request=None):
        self.app = app
        if request is None:
            request = app.request_class(environ)
        self.request = request
        self.url_adapter = app.create_url_adapter(self.request)

        self.match_request()
        
    def match_request(self):
        """Can be overridden by a subclass to hook into the matching
        of the request.
        """
        try:
            url_rule, self.request.view_args = \
                self.url_adapter.match(return_rule=True)
            self.request.url_rule = url_rule
        except HTTPException as e:
            self.request.routing_exception = e
            
    def push(self):
        """Binds the request context to the current context."""
        # If an exception occurs in debug mode or if context preservation is
        # activated under exception situations exactly one context stays
        # on the stack.  The rationale is that you want to access that
        # information under debug situations.  However if someone forgets to
        # pop that context again we want to make sure that on the next push
        # it's invalidated, otherwise we run at risk that something leaks
        # memory.  This is usually only a problem in test suite since this
        # functionality is not active in production environments.
        top = _request_ctx_stack.top
        if top is not None and top.preserved:
            top.pop(top._preserved_exc)

        # Before we push the request context we have to ensure that there
        # is an application context.
        app_ctx = _app_ctx_stack.top
        if app_ctx is None or app_ctx.app != self.app:
            app_ctx = self.app.app_context()
            app_ctx.push()
            self._implicit_app_ctx_stack.append(app_ctx)
        else:
            self._implicit_app_ctx_stack.append(None)

        if hasattr(sys, 'exc_clear'):
            sys.exc_clear()

        _request_ctx_stack.push(self)

        # Open the session at the moment that the request context is
        # available. This allows a custom open_session method to use the
        # request context (e.g. code that access database information
        # stored on `g` instead of the appcontext).
        self.session = self.app.open_session(self.request)
        if self.session is None:
            self.session = self.app.make_null_session()

