'''Created on 2018年3月23日 @author: litian'''
from functools import partial
from werkzeug.local import LocalStack, LocalProxy


_request_ctx_err_msg = '''\
Working outside of request context.

This typically means that you attempted to use functionality that needed
an active HTTP request.  Consult the documentation on testing for
information about how to avoid this problem.\
'''
_app_ctx_err_msg = '''\
Working outside of application context.

This typically means that you attempted to use functionality that needed
to interface with the current application object in a way.  To solve
this set up an application context with app.app_context().  See the
documentation for more information.\
'''


def _lookup_req_object(name):
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError(_request_ctx_err_msg)
    return getattr(top, name)


def _lookup_app_object(name):
    top = _app_ctx_stack.top
    if top is None:
        raise RuntimeError(_app_ctx_err_msg)
    return getattr(top, name)


def _find_app():
    top = _app_ctx_stack.top
    if top is None:
        raise RuntimeError(_app_ctx_err_msg)
    return top.app


# context locals
_request_ctx_stack = LocalStack()       # 请求上下文的数据结构
_app_ctx_stack = LocalStack()           # 应用上下文的数据结构
current_app = LocalProxy(_find_app)     # 从这个开始的4个，都是全局变量，他们其实通过代理上下文来实现的  

# request = LocalProxy(_request_ctx_stack.top.request) = LocalProxy (_request_ctx_stack._local[stack][-1].request)
request = LocalProxy(partial(_lookup_req_object, 'request')) 
   
session = LocalProxy(partial(_lookup_req_object, 'session'))
g = LocalProxy(partial(_lookup_app_object, 'g'))