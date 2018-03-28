#!/usr/bin/python3
# -*- coding=utf-8 -*-
from threading import Lock

class Flask(_PackageBoundObject):
    
    
    def __init__(self, import_name, static_path=None, static_url_path=None,
                 static_folder='static', template_folder='templates',
                 instance_path=None, instance_relative_config=False,
                 root_path=None):
        _PackageBoundObject.__init__(self, import_name,
                                     template_folder=template_folder,
                                     root_path=root_path)
        
        self.view_functions = {}
        self.url_map = Map()
        
        self._got_first_request = False
        self._before_request_lock = Lock()
    
    def run(self, host=None, port=None, debug=None, **options):
        """Runs the application on a local development server.
        @ 监听在指定的端口，收到 HTTP 请求的时候解析为 WSGI 格式，然后调用 app 去执行处理的逻辑
        """
        from werkzeug.serving import run_simple
        
        if host is None:
            host = '127.0.0.1'
        if port is None:
            server_name = self.config['SERVER_NAME']
            if server_name and ':' in server_name:
                port = int(server_name.rsplit(':', 1)[1])
            else:
                port = 5000
        
        # 调用 werkzeug.serving 模块的 run_simple 函数，传入收到的参数
        # 注意第三个参数传进去的是 self，也就是要执行的 web application
        try:
            run_simple(host, port, self, **options)
        finally:
            self._got_first_request = False
            
    def __call__(self, environ, start_response):
        """Shortcut for :attr:`wsgi_app`."""
        return self.wsgi_app(environ, start_response)  
    
    def wsgi_app(self, environ, start_response):
        """The actual WSGI application. 
        @ 找到处理函数，然后调用它
        """
        # 生成request对象和上下文环境，并把它压栈。
        ctx = self.request_context(environ)
        ctx.push()
        error = None
        try:
            try:
                # 正确的请求处理路径，会通过路由找到对应的处理函数
                response = self.full_dispatch_request() # full_dispatch_request起到了预处理和错误处理以及分发请求的作用  
            except Exception as e:
                # 错误处理，默认是 InternalServerError 错误处理函数，客户端会看到服务器 500 异常
                error = e
                response = self.handle_exception(e) # 如果有错误发生，则生成错误响应  
            return response(environ, start_response)# 如果没有错误发生，则正常响应请求，返回响应内容  
        finally:
            if self.should_ignore_error(error):
                error = None
            # 不管处理是否发生异常，都需要把栈中的请求 pop 出来
            ctx.auto_pop(error)
            
    def request_context(self, environ):
        """Creates a :class:`~flask.ctx.RequestContext` from the given
        environment and binds it to the current context.  This must be used in
        combination with the ``with`` statement because the request is only bound
        to the current context for the duration of the ``with`` block.
        Example usage::

            with app.request_context(environ):
                do_something_with(request)

        The object returned can also be used without the ``with`` statement
        which is useful for working in the shell.  The example above is
        doing exactly the same as this code::

            ctx = app.request_context(environ)
            ctx.push()
            try:
                do_something_with(request)
            finally:
                ctx.pop()
        """
        return RequestContext(self, environ)
            
    def full_dispatch_request(self):
        """Dispatches the request and on top of that performs request
        pre and postprocessing as well as HTTP exception catching and
        error handling.
        @ self.dispatch_request() 返回的是处理函数的返回结果（比如 hello world 例子中返回的字符串），finalize_request 会把它转换成 Response 对象。
        """
        self.try_trigger_before_first_request_functions()   # 进行发生真实请求前的处理 ，目的是，最后将_got_first_request属性置为True.
        try:
            request_started.send(self)      # socket部分的操作  request_started = _signals.signal('request-started')
            rv = self.preprocess_request()  # 进行请求的预处理 ，主要是进行flask的hook钩子, before_request功能的实现，也就是在真正发生请求之前，有些事情需要提前做
            if rv is None:
                rv = self.dispatch_request()        # 进行请求判定和分发
        except Exception as e:
            rv = self.handle_user_exception(e)
        return self.finalize_request(rv)      
        """
        @ 在 dispatch_request 之前我们看到 preprocess_request，之后看到 finalize_request，它们里面包括了请求处理之前和处理之后的很多 hooks 。这些 hooks 包括：
        @ 第一次请求处理之前的 hook 函数，通过 before_first_request 定义
        @ 每个请求处理之前的 hook 函数，通过 before_request 定义
        @ 每个请求正常处理之后的 hook 函数，通过 after_request 定义
        @ 不管请求是否异常都要执行的 teardown_request hook 函数
        @ dispatch_request 要做的就是找到我们的处理函数，并返回调用的结果，也就是路由的过程
        """
    
    def dispatch_request(self):
        """Does the request dispatching.  Matches the URL and returns the
        return value of the view or error handler.  This does not have to
        be a response object.  In order to convert the return value to a
        proper response object, call :func:`make_response`.
        """
        req = _request_ctx_stack.top.request    # 将请求对象赋值给req
        if req.routing_exception is not None:
            self.raise_routing_exception(req)
        rule = req.url_rule
        return self.view_functions[rule.endpoint](**req.view_args)
        """
        _request_ctx_stack.top.request 保存着当前请求的信息，在每次请求过来的时候，flask 会把当前请求的信息保存进去，这样我们就能在整个请求处理过程中使用它
        """
        
    def finalize_request(self, rv, from_error_handler=False):
        """Given the return value from a view function this finalizes
        the request by converting it into a response and invoking the
        postprocessing functions.  This is invoked for both normal
        request dispatching as well as error handlers.
        """
        response = self.make_response(rv)
        try:
            response = self.process_response(response)  # 主要是处理一个after_request的功能，比如你在请求后，要把数据库连接关闭等动作，和上面提到的before_request对应和类似。
            request_finished.send(self, response=response)  # request_finished = _signals.signal('request-finished')
        except Exception:
            if not from_error_handler:
                raise
            self.logger.exception('Request finalizing failed with an '
                                  'error while handling an error')
        return response
    
    def make_response(self, rv):
        """Converts the return value from a view function to a real
        response object that is an instance of :attr:`response_class`.
        """
        status_or_headers = headers = None
        if isinstance(rv, tuple):
            rv, status_or_headers, headers = rv + (None,) * (3 - len(rv))

        if rv is None:
            raise ValueError('View function did not return a response')

        if isinstance(status_or_headers, (dict, list)):
            headers, status_or_headers = status_or_headers, None

        if not isinstance(rv, self.response_class):
            # When we create a response object directly, we let the constructor
            # set the headers and status.  We do this because there can be
            # some extra logic involved when creating these objects with
            # specific values (like default content type selection).
            if isinstance(rv, (text_type, bytes, bytearray)):
                rv = self.response_class(rv, headers=headers,
                                         status=status_or_headers)
                headers = status_or_headers = None
            else:
                rv = self.response_class.force_type(rv, request.environ)

        if status_or_headers is not None:
            if isinstance(status_or_headers, string_types):
                rv.status = status_or_headers
            else:
                rv.status_code = status_or_headers
        if headers:
            rv.headers.extend(headers)

        return rv

    
    def create_url_adapter(self, request):
        """Creates a URL adapter for the given request.  The URL adapter
        is created at a point where the request context is not yet set up
        so the request is passed explicitly.
        """
        if request is not None:
            return self.url_map.bind_to_environ(request.environ,
                server_name=self.config['SERVER_NAME'])
        # We need at the very least the server name to be set for this
        # to work.
        if self.config['SERVER_NAME'] is not None:
            return self.url_map.bind(
                self.config['SERVER_NAME'],
                script_name=self.config['APPLICATION_ROOT'] or '/',
                url_scheme=self.config['PREFERRED_URL_SCHEME'])
    
        
    
    def route(self, rule, **options):
        """A decorator that is used to register a view function for a
        given URL rule.  This does the same thing as :meth:`add_url_rule`
        but is intended for decorator usage::
        """
        def decorator(f):
            endpoint = options.pop('endpoint', None)
            self.add_url_rule(rule, endpoint, f, **options)
            return f
        return decorator
    
    @setupmethod
    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        """Connects a URL rule.  Works exactly like the :meth:`route`
        decorator.  If a view_func is provided it will be registered with the
        endpoint.
        """
        methods = options.pop('methods', None)

        rule = self.url_rule_class(rule, methods=methods, **options)

        self.url_map.add(rule)
        if view_func is not None:
            old_func = self.view_functions.get(endpoint)
            if old_func is not None and old_func != view_func:
                raise AssertionError('View function mapping is overwriting an '
                                     'existing endpoint function: %s' % endpoint)
            self.view_functions[endpoint] = view_func
    
    
    
    
    
    def try_trigger_before_first_request_functions(self):
        """Called before each request and will ensure that it triggers
        the :attr:`before_first_request_funcs` and only exactly once per
        application instance (which means process usually).
        """
        if self._got_first_request:
            return
        with self._before_request_lock:
            if self._got_first_request:
                return
            for func in self.before_first_request_funcs:
                func()
            self._got_first_request = True
    
    @property
    def got_first_request(self):
        """This attribute is set to ``True`` if the application started
        handling the first request.
        """
        return self._got_first_request      # 默认返回False
    