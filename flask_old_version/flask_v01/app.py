#!/usr/bin/python3
# -*- coding=utf-8 -*-
""""
Flask0.1版本源码分析
"""

class Flask(object):
    """The flask object implements a WSGI application and acts as the central
    object.  It is passed the name of the module or package of the
    application.  Once it is created it will act as a central registry for
    the view functions, the URL rules, template configuration and much more.
    """
    request_class = Request
    
    response_class = Response

    static_path = '/static'

    secret_key = None

    session_cookie_name = 'session'

    jinja_options = dict(
        autoescape=True,
        extensions=['jinja2.ext.autoescape', 'jinja2.ext.with_']
    )

    def __init__(self, package_name):
        """
        self.view_functions: {f.__name__: f} 例如：{'hello': hello}
        self.url_map:  Map([Rule('/', endpoint='index'),
                            Rule('/downloads/', endpoint='downloads/index'),
                            Rule('/downloads/<int:id>', endpoint='downloads/show')])
                            
                        Map([<Rule '/' (GET, HEAD, OPTIONS) -> index>,
                             <Rule '/static/<filename>' (GET, HEAD, OPTIONS) -> static>,
                             <Rule '/user/<name>' (GET, HEAD, OPTIONS) -> user>])
        """
        self.debug = False
        self.package_name = package_name
        self.root_path = _get_package_path(self.package_name)
        self.template_context_processors = [_default_template_ctx_processor]

        self.view_functions = {}    # 保存了视图函数，处理用户请求的函数。 在调用route()装饰器的时候被赋值的，保存了视图函数名到函数体的映射

        self.url_map = Map()    # 用以保存URI到视图函数的映射，即保存app.route()这个装饰器的信息。调用add_url_rule()来给self.url_map赋值，用以保存URI到视图函数的名映射
        
        self.error_handlers = {}    # 保存了错误处理函数 
        self.before_request_funcs = []  # 保存了请求的预处理函数
        self.after_request_funcs = []   # 保存请求后处理函数

    def route(self, rule, **options):
        """A decorator that is used to register a view function for a
        given URL rule.  Example::
        """
        def decorator(f):
            self.add_url_rule(rule, f.__name__, **options)
            self.view_functions[f.__name__] = f
            return f
        return decorator
    
    def add_url_rule(self, rule, endpoint, **options):
        """Connects a URL rule.  Works exactly like the :meth:`route`
        decorator but does not register the view function for the endpoint.
        """
        options['endpoint'] = endpoint
        options.setdefault('methods', ('GET',))
        self.url_map.add(Rule(rule, **options))
        
    def run(self, host='localhost', port=5000, **options):
        """Runs the application on a local development server.  If the
        :attr:`debug` flag is set the server will automatically reload
        for code changes and show a debugger in case an exception happened.
        """
        from werkzeug import run_simple
        if 'debug' in options:
            self.debug = options.pop('debug')
        options.setdefault('use_reloader', self.debug)
        options.setdefault('use_debugger', self.debug)
        return run_simple(host, port, self, **options)  # 调用run_simple来启动了一个WSGI server
    
    def __call__(self, environ, start_response):
        """Shortcut for :attr:`wsgi_app`"""
        return self.wsgi_app(environ, start_response)
    
    def wsgi_app(self, environ, start_response):
        """The actual WSGI application.  This is not implemented in
        `__call__` so that middlewares can be applied:
        """
        with self.request_context(environ):     # 在Flask对象调用run()之后，每当有请求进入时，都会将请求上下文入栈；在处理完请求后，再出栈
            rv = self.preprocess_request()
            if rv is None:
                rv = self.dispatch_request()
            response = self.make_response(rv)   # 将这个返回值转化为一个真正的response对象
            response = self.process_response(response)
            return response(environ, start_response)
        
    def request_context(self, environ):
        """Creates a request context from the given environment and binds
        it to the current context.  This must be used in combination with
        the `with` statement because the request is only bound to the
        current context for the duration of the `with` block.
        """
        return _RequestContext(self, environ)
    
    def dispatch_request(self):
        """Does the request dispatching.  Matches the URL and returns the
        return value of the view or error handler.  This does not have to
        be a response object.  In order to convert the return value to a
        proper response object, call :func:`make_response`.
        """
        endpoint, values = self.match_request()
        return self.view_functions[endpoint](**values)
        
    def match_request(self):
        """Matches the current request against the URL map and also
        stores the endpoint and view arguments on the request object
        is successful, otherwise the exception is stored.
        """
        rv = _request_ctx_stack.top.url_adapter.match()
        request.endpoint, request.view_args = rv
        return rv
    
    def make_response(self, rv):
        """Converts the return value from a view function to a real
        response object that is an instance of :attr:`response_class`.
        """
        if isinstance(rv, self.response_class):
            return rv
        if isinstance(rv, basestring):
            return self.response_class(rv)
        if isinstance(rv, tuple):
            return self.response_class(*rv)
        return self.response_class.force_type(rv, request.environ)
    
    def process_response(self, response):
        """Can be overridden in order to modify the response object
        before it's sent to the WSGI server.  By default this will
        call all the :meth:`after_request` decorated functions.
        """
        session = _request_ctx_stack.top.session
        if session is not None:
            self.save_session(session, response)    # 保存有更新的会话信息
        for handler in self.after_request_funcs:    # 遍历这个数组中的函数，来处理reponse
            response = handler(response)
        return response
    
    def save_session(self, session, response):
        """Saves the session if it needs updates.  For the default
        implementation, check :meth:`open_session`.
        """
        if session is not None:
            session.save_cookie(response, self.session_cookie_name)
        
        
        
        
        
    
    
    
        
class _RequestContext(object):
    """The request context contains all request relevant information.  It is
    created at the beginning of the request and pushed to the
    `_request_ctx_stack` and removed at the end of it.  It will create the
    URL adapter and request object for the WSGI environment provided.
    """

    def __init__(self, app, environ):
        self.app = app
        self.url_adapter = app.url_map.bind_to_environ(environ)
        self.request = app.request_class(environ)
        self.session = app.open_session(self.request)
        self.g = _RequestGlobals()
        self.flashes = None

    def __enter__(self):
        _request_ctx_stack.push(self)

    def __exit__(self, exc_type, exc_value, tb):
        # do not pop the request stack if we are in debug mode and an
        # exception happened.  This will allow the debugger to still
        # access the request object in the interactive shell.
        if tb is None or not self.app.debug:
            _request_ctx_stack.pop()
        
        
class _RequestGlobals(object):
    pass


_request_ctx_stack = LocalStack()
current_app = LocalProxy(lambda: _request_ctx_stack.top.app)
request = LocalProxy(lambda: _request_ctx_stack.top.request)
session = LocalProxy(lambda: _request_ctx_stack.top.session)
g = LocalProxy(lambda: _request_ctx_stack.top.g)
        
        
################################################################################


        
        
        
        
        
        
        
        
        
        
        
        
        
        