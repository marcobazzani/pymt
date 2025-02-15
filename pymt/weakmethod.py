'''
WeakMethod: implementation of weakref for function and bounded method.

This class is used in Clock class, to prevent the clock of taking memory if the
object is deleted. Check examples/core/clock_method.py for more informations.

This WeakMethod class is taken from the recipe
http://code.activestate.com/recipes/81253/,
based on the nicodemus version. (thanks to him !)
'''

import weakref
from types import MethodType as instancemethod

class WeakMethod(object):
    def __init__(self, method):
        try:
            if method.__self__ is not None:
                # bound method
                self._obj = weakref.ref(method.__self__)
            else:
                # unbound method
                self._obj = None
            self._func = method.__func__
            self._class = method.__self__.__class__
        except AttributeError:
            # not a method
            self._obj = None
            self._func = method
            self._class = None

    def __call__(self):
        '''Return a new bound-method like the original, or the
        original function if refers just to a function or unbound
        method.
        Returns None if the original object doesn't exist
        '''
        if self.is_dead():
            return None
        if self._obj is not None:
            # we have an instance: return a bound method
            return instancemethod(self._func, self._obj(), self._class)
        else:
            # we don't have an instance: return just the function
            return self._func


    def is_dead(self):
        '''Returns True if the referenced callable was a bound method and
        the instance no longer exists. Otherwise, return False.
        '''
        return self._obj is not None and self._obj() is None


    def __eq__(self, other):
        try:
            return type(self) is type(other) and self() == other()
        except:
            return False

    def __ne__(self, other):
        return not self == other

