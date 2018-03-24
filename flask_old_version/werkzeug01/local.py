'''Created on 2018年3月24日@author: litian'''
from _thread import get_ident

class Local(object):

    def __init__(self):
        object.__setattr__(self, '__storage__', {})         # 相当于 __storage__ = {}
        object.__setattr__(self, '__ident_func__', get_ident)# 相当于  __ident__func__ = get_ident

    def __getattr__(self, name):
        """
        {'thread_id1': {'stack': [_RequestContext()]},
        'thread_id2': {'stack': [_RequestContext()]}}
        """
        try:
            return self.__storage__[self.__ident_func__()][name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        """
        {'thread_id1': {'stack': [_RequestContext()]},
        'thread_id2': {'stack': [_RequestContext()]}}
        """
        ident = self.__ident_func__()   # 获取线程id
        storage = self.__storage__      # storage = {}
        try:
            storage[ident][name] = value
        except KeyError:
            storage[ident] = {name: value}




class LocalStack(object):

    def __init__(self):
        self._local = Local()

    def push(self, obj):
        rv = getattr(self._local, 'stack', None)
        if rv is None:
            self._local.stack = rv = []         # stack被初始化一个数组，作为栈来使用,实际上是在调用 __setattr__(self, name, value)
        rv.append(obj)
        return rv

    def pop(self):
        stack = getattr(self._local, 'stack', None)
        if stack is None:
            return None
        elif len(stack) == 1:
            release_local(self._local)
            return stack[-1]
        else:
            return stack.pop()
        
    @property
    def top(self):
        """The topmost item on the stack.  If the stack is empty,
        `None` is returned.
        """
        try:
            return self._local.stack[-1]        # top()返回的就是self._local.stack栈顶元素（即数组中末尾元素）
        except (AttributeError, IndexError):
            return None
        