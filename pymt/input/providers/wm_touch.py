'''
WM_TOUCH: Support of WM_TOUCH message (Window platform)
'''

__all__ = ('WM_TouchProvider', 'WM_Touch')

import os
from pymt.input.providers.wm_common import WM_TABLET_QUERYSYSTEMGESTURE, \
        GWL_WNDPROC, QUERYSYSTEMGESTURE_WNDPROC, WM_TOUCH, WM_MOUSEMOVE, \
        WM_MOUSELAST, PEN_OR_TOUCH_MASK, PEN_OR_TOUCH_SIGNATURE, \
        PEN_EVENT_TOUCH_MASK, TOUCHEVENTF_UP, TOUCHEVENTF_DOWN, \
        TOUCHEVENTF_MOVE
from pymt.input.touch import Touch
from pymt.input.shape import TouchShapeRect

class WM_Touch(Touch):
    '''Touch representing the WM_Touch event. Support pos, shape and size profiles'''
    __attrs__ = ('size', )
    def depack(self, args):
        self.shape = TouchShapeRect()
        self.sx, self.sy = args[0], args[1]
        self.shape.width = args[2][0]
        self.shape.height = args[2][1]
        self.size = self.shape.width * self.shape.height
        self.profile = ('pos', 'shape', 'size')

        super(WM_Touch, self).depack(args)

    def __str__(self):
        return '<WMTouch id:%d uid:%d pos:%s device:%s>' % (self.id, self.uid, str(self.spos), self.device)

if 'PYMT_DOC' in os.environ:
    # documentation hack
    WM_TouchProvider = None

else:
    from ctypes import wintypes, windll, WINFUNCTYPE, c_long, c_int, \
            Structure, pointer, sizeof, byref
    from collections import deque
    from pymt.input.provider import TouchProvider
    from pymt.input.factory import TouchFactory

    # check availability of RegisterTouchWindow
    if not hasattr(windll.user32, 'RegisterTouchWindow'):
        raise Exception('Unsupported Window version')

    WNDPROC = WINFUNCTYPE(c_long, c_int, c_int, c_int, c_int)

    class TOUCHINPUT(Structure):
        _fields_ = [
            ('x',wintypes.LONG),
            ('y',wintypes.LONG),
            ('pSource',wintypes.HANDLE),
            ('id',wintypes.DWORD),
            ('flags',wintypes.DWORD),
            ('mask',wintypes.DWORD),
            ('time',wintypes.DWORD),
            ('extraInfo',wintypes.ULONG ),
            ('size_x',wintypes.DWORD),
            ('size_y',wintypes.DWORD)
        ]

        def size(self):
            return (self.size_x, self.size_y)

        def screen_x(self):
            return self.x/100.0

        def screen_y(self):
            return self.y/100.0

        def _event_type(self):
            if self.flags & TOUCHEVENTF_MOVE:
                return 'move'
            if self.flags & TOUCHEVENTF_DOWN:
                return 'down'
            if self.flags & TOUCHEVENTF_UP:
                return 'up'
        event_type = property(_event_type)


    class RECT(Structure):
        _fields_ = [
            ('left',   wintypes.ULONG ),
            ('top',    wintypes.ULONG ),
            ('right',  wintypes.ULONG ),
            ('bottom', wintypes.ULONG )
        ]

        x = property(lambda self: self.left)
        y = property(lambda self: self.top)
        w = property(lambda self: self.right-self.left)
        h = property(lambda self: self.bottom-self.top)


    class WM_TouchProvider(TouchProvider):

        def start(self):
            self.touch_events = deque()
            self.touches = {}
            self.uid = 0

            # get window handle, and register to recive WM_TOUCH messages
            self.hwnd = windll.user32.GetActiveWindow()
            windll.user32.RegisterTouchWindow(self.hwnd, 1)

            # inject our own wndProc to handle messages before window manager does
            self.new_windProc = WNDPROC(self._touch_wndProc)
            self.old_windProc = windll.user32.SetWindowLongW(
                self.hwnd,
                GWL_WNDPROC,
                self.new_windProc
            )


        def update(self, dispatch_fn):
            win_rect = RECT()
            windll.user32.GetWindowRect(self.hwnd, byref(win_rect))

            while True:
                try:
                    t = self.touch_events.pop()
                except:
                    break

                # adjust x,y to window coordinates (0.0 to 1.0)
                x = (t.screen_x()-win_rect.x)/float(win_rect.w)
                y = 1.0 - (t.screen_y()-win_rect.y)/float(win_rect.h)

                # actually dispatch input
                if t.event_type == 'down':
                    self.uid += 1
                    self.touches[t.id] = WM_Touch(self.device,
                                                  self.uid, [x, y, t.size()])
                    dispatch_fn('down', self.touches[t.id] )

                if t.event_type == 'move' and t.id in self.touches:
                    self.touches[t.id].move([x, y, t.size()])
                    dispatch_fn('move', self.touches[t.id] )

                if t.event_type == 'up'  and t.id in self.touches:
                    self.touches[t.id].move([x, y, t.size()])
                    dispatch_fn('up', self.touches[t.id] )
                    del self.touches[t.id]


        def stop(self):
            windll.user32.UnregisterTouchWindow(self.hwnd)
            self.new_windProc = windll.user32.SetWindowLongW(
                self.hwnd,
                GWL_WNDPROC,
                self.old_windProc
            )


        # we inject this wndProc into our main window, to process
        # WM_TOUCH and mouse messages before the window manager does
        def _touch_wndProc( self, hwnd, msg, wParam, lParam ):
            done = False
            if msg == WM_TABLET_QUERYSYSTEMGESTURE:
                return QUERYSYSTEMGESTURE_WNDPROC

            if msg == WM_TOUCH:
                done = self._touch_handler(msg, wParam, lParam)

            if msg >= WM_MOUSEMOVE and msg <= WM_MOUSELAST:
                done = self._mouse_handler(msg, wParam, lParam)

            if not done:
                return windll.user32.CallWindowProcW( self.old_windProc, hwnd, msg, wParam, lParam)
            return 1


        # this on pushes WM_TOUCH messages onto our event stack
        def _touch_handler(self, msg, wParam, lParam):
            touches = (TOUCHINPUT * wParam)()
            windll.user32.GetTouchInputInfo(wintypes.HANDLE(lParam),
                                            wParam,
                                            pointer(touches),
                                            sizeof(TOUCHINPUT))
            for i in range(wParam):
                self.touch_events.appendleft(touches[i])
            return True


        # filter fake mouse events, because touch and stylus also make mouse events
        def _mouse_handler(self, msg, wparam, lParam):
            info = windll.user32.GetMessageExtraInfo()
            if (info & PEN_OR_TOUCH_MASK) == PEN_OR_TOUCH_SIGNATURE: # its a touch or a pen
                if info & PEN_EVENT_TOUCH_MASK:
                    return True


    TouchFactory.register('wm_touch', WM_TouchProvider)
