'''
Tuio: TUIO input provider implementation
'''

__all__ = ('TuioTouchProvider', 'Tuio2dCurTouch', 'Tuio2dObjTouch')

import osc
from collections import deque
from pymt.input.provider import TouchProvider
from pymt.input.factory import TouchFactory
from pymt.input.touch import Touch
from pymt.input.shape import TouchShapeRect
from pymt.logger import pymt_logger

class TuioTouchProvider(TouchProvider):
    '''Tuio provider listen to a socket, and handle part of OSC message

        * /tuio/2Dcur
        * /tuio/2Dobj

    Tuio provider can be configured with the `[`input`]` configuration ::

        [input]
        # name = tuio,<ip>:<port>
        multitouchtable = tuio,192.168.0.1:3333

    You can easily handle new tuio path by extending the providers like this ::

        # Create a class to handle the new touch type
        class TuioNEWPATHTouch(Touch):
            def __init__(self, id, args):
                super(TuioNEWPATHTouch, self).__init__(id, args)

            def depack(self, args):
                # Write here the depack function of args.
                # for a simple x, y, value, you can do this :
                if len(args) == 2:
                    self.sx, self.sy = args
                    self.profile = ('pos', )
                self.sy = 1 - self.sy
                super(TuioNEWPATHTouch, self).depack(args)

        # Register it to tuio touch provider
        TuioTouchProvider.register('/tuio/NEWPATH', TuioNEWPATHTouch)
    '''

    __handlers__ = {}

    def __init__(self, device, args):
        super(TuioTouchProvider, self).__init__(device, args)
        args = args.split(',')
        if len(args) <= 0:
            pymt_logger.error('Tuio: Invalid configuration for TUIO provider')
            pymt_logger.error('Tuio: Format must be ip:port (eg. 127.0.0.1:3333)')
            pymt_logger.error('Tuio: Actual TUIO configuration is <%s>' % (str(','.join(args))))
            return None
        ipport = args[0].split(':')
        if len(ipport) != 2:
            pymt_logger.error('Tuio: Invalid configuration for TUIO provider')
            pymt_logger.error('Tuio: Format must be ip:port (eg. 127.0.0.1:3333)')
            pymt_logger.error('Tuio: Actual TUIO configuration is <%s>' % (str(','.join(args))))
            return None
        self.ip, self.port = args[0].split(':')
        self.port = int(self.port)
        self.handlers = {}
        self.oscid = None
        self.tuio_event_q = deque()
        self.touches = {}

    @staticmethod
    def register(oscpath, classname):
        '''Register a new path to handle in tuio provider'''
        TuioTouchProvider.__handlers__[oscpath] = classname

    @staticmethod
    def unregister(oscpath, classname):
        '''Unregister a new path to handle in tuio provider'''
        if oscpath in TuioTouchProvider.__handlers__:
            del TuioTouchProvider.__handlers__[oscpath]

    @staticmethod
    def create(oscpath, **kwargs):
        '''Create a touch from a tuio path'''
        if oscpath not in TuioTouchProvider.__handlers__:
            raise Exception('Unknown %s touch path' % oscpath)
        return TuioTouchProvider.__handlers__[oscpath](**kwargs)

    def start(self):
        '''Start the tuio provider'''
        self.oscid = osc.listen(self.ip, self.port)
        for oscpath in TuioTouchProvider.__handlers__:
            self.touches[oscpath] = {}
            osc.bind(self.oscid, self._osc_tuio_cb, oscpath)

    def stop(self):
        '''Stop the tuio provider'''
        osc.dontListen(self.oscid)

    def update(self, dispatch_fn):
        '''Update the tuio provider (pop event from the queue)'''

        # deque osc queue
        osc.readQueue(self.oscid)

        # read the Queue with event
        while True:
            try:
                value = self.tuio_event_q.pop()
            except IndexError:
                # queue is empty, we're done for now
                return
            self._update(dispatch_fn, value)

    def _osc_tuio_cb(self, *incoming):
        message = incoming[0]
        oscpath, types, args = message[0], message[1], message[2:]
        self.tuio_event_q.appendleft([oscpath, args, types])

    def _update(self, dispatch_fn, value):
        oscpath, args, types = value
        command = args[0]

        # verify commands
        if command not in ['alive', 'set']:
            return

        # move or create a new touch
        if command == 'set':
            id = args[1]
            if id not in self.touches[oscpath]:
                # new touch
                touch = TuioTouchProvider.__handlers__[oscpath](self.device, id, args[2:])
                self.touches[oscpath][id] = touch
                dispatch_fn('down', touch)
            else:
                # update a current touch
                touch = self.touches[oscpath][id]
                touch.move(args[2:])
                dispatch_fn('move', touch)

        # alive event, check for deleted touch
        if command == 'alive':
            alives = args[1:]
            to_delete = []
            for id in self.touches[oscpath]:
                if not id in alives:
                    # touch up
                    touch = self.touches[oscpath][id]
                    if not touch in to_delete:
                        to_delete.append(touch)

            for touch in to_delete:
                dispatch_fn('up', touch)
                del self.touches[oscpath][touch.id]

class TuioTouch(Touch):
    '''Abstraction for TUIO touch.

    Depending of the tracker, the TuioTouch object support
    multiple profiles as :

        * fiducial : name markerid, property .fid
        * position : name pos, property .x, .y
        * angle : name angle, property .a
        * velocity vector : name mov, property .X, .Y
        * rotation velocity : name rot, property .A
        * motion acceleration : name motacc, property .m
        * rotation acceleration : name rotacc, property .r
    '''
    __attrs__ = ('a', 'b', 'c', 'X', 'Y', 'Z', 'A', 'B', 'C', 'm', 'r')

    def __init__(self, device, id, args):
        super(TuioTouch, self).__init__(device, id, args)
        # Default argument for TUIO touches
        self.a = 0.0
        self.b = 0.0
        self.c = 0.0
        self.X = 0.0
        self.Y = 0.0
        self.Z = 0.0
        self.A = 0.0
        self.B = 0.0
        self.C = 0.0
        self.m = 0.0
        self.r = 0.0

    angle = property(lambda self: self.a)
    mot_accel = property(lambda self: self.m)
    rot_accel = property(lambda self: self.r)
    xmot = property(lambda self: self.X)
    ymot = property(lambda self: self.Y)
    zmot = property(lambda self: self.Z)

class Tuio2dCurTouch(TuioTouch):
    '''A 2dCur TUIO touch.'''
    def __init__(self, device, id, args):
        super(Tuio2dCurTouch, self).__init__(device, id, args)

    def depack(self, args):
        if len(args) < 5:
            self.sx, self.sy = list(map(float, args[0:2]))
            self.profile = ('pos', )
        elif len(args) == 5:
            self.sx, self.sy, self.X, self.Y, self.m = list(map(float, args[0:5]))
            self.Y = -self.Y
            self.profile = ('pos', 'mov', 'motacc')
        else:
            self.sx, self.sy, self.X, self.Y, self.m, width, height = list(map(float, args[0:7]))
            self.Y = -self.Y
            self.profile = ('pos', 'mov', 'motacc', 'shape')
            if self.shape is None:
                self.shape = TouchShapeRect()
            self.shape.width = width
            self.shape.height = height
        self.sy = 1 - self.sy
        super(Tuio2dCurTouch, self).depack(args)


class Tuio2dObjTouch(TuioTouch):
    '''A 2dObj TUIO object.
    '''
    def __init__(self, device, id, args):
        super(Tuio2dObjTouch, self).__init__(device, id, args)

    def depack(self, args):
        if len(args) < 5:
            self.sx, self.sy = args[0:2]
            self.profile = ('pos', )
        elif len(args) == 9:
            self.fid, self.sx, self.sy, self.a, self.X, self.Y, self.A, self.m, self.r = args[0:9]
            self.Y = -self.Y
            self.profile = ('markerid', 'pos', 'angle', 'mov', 'rot', 'motacc', 'rotacc')
        else:
            self.fid, self.sx, self.sy, self.a, self.X, self.Y, self.A, self.m, self.r, width, height = args[0:11]
            self.Y = -self.Y
            self.profile = ('markerid', 'pos', 'angle', 'mov', 'rot', 'rotacc',
                            'acc', 'shape')
            if self.shape is None:
                self.shape = TouchShapeRect()
                self.shape.width = width
                self.shape.height = height
        self.sy = 1 - self.sy
        super(Tuio2dObjTouch, self).depack(args)

# registers
TuioTouchProvider.register('/tuio/2Dcur', Tuio2dCurTouch)
TuioTouchProvider.register('/tuio/2Dobj', Tuio2dObjTouch)
TouchFactory.register('tuio', TuioTouchProvider)
