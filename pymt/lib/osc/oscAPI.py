'''    simpleOSC 0.2
    ixi software - July, 2006
    www.ixi-software.net

    simple API  for the Open SoundControl for Python (by Daniel Holth, Clinton
    McChesney --> pyKit.tar.gz file at http://wiretap.stetson.edu)
    Documentation at http://wiretap.stetson.edu/docs/pyKit/

    The main aim of this implementation is to provide with a simple way to deal
    with the OSC implementation that makes life easier to those who don't have
    understanding of sockets or programming. This would not be on your screen without the help
    of Daniel Holth.

    This library is free software; you can redistribute it and/or
    modify it under the terms of the GNU Lesser General Public
    License as published by the Free Software Foundation; either
    version 2.1 of the License, or (at your option) any later version.

    This library is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this library; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

    Thanks for the support to Buchsenhausen, Innsbruck, Austria.
'''

import OSC
import socket, os, time, errno
from threading import Thread
from pymt.logger import pymt_logger

# globals
outSocket = 0
addressManager = None
oscThreads = {}

def init() :
    '''instantiates address manager and outsocket as globals
    '''
    global outSocket, addressManager
    if addressManager is not None:
        return
    outSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    addressManager = OSC.CallbackManager()


def bind(func, oscaddress):
    '''bind given oscaddresses with given functions in address manager
    '''
    addressManager.add(func, oscaddress)


def sendMsg(oscAddress, dataArray=[], ipAddr='127.0.0.1', port=9000) :
    '''create and send normal OSC msgs
        defaults to '127.0.0.1', port 9000
    '''
    outSocket.sendto( createBinaryMsg(oscAddress, dataArray),  (ipAddr, port))


def createBundle():
    '''create bundled type of OSC messages
    '''
    b = OSC.OSCMessage()
    b.address = ""
    b.append("#bundle")
    b.append(0)
    b.append(0)
    return b


def appendToBundle(bundle, oscAddress, dataArray):
    '''create OSC mesage and append it to a given bundle
    '''
    bundle.append( createBinaryMsg(oscAddress, dataArray),  'b')


def sendBundle(bundle, ipAddr='127.0.0.1', port=9000) :
    '''convert bundle to a binary and send it
    '''
    outSocket.sendto(bundle.message, (ipAddr, port))


def createBinaryMsg(oscAddress, dataArray):
    '''create and return general type binary OSC msg
    '''
    m = OSC.OSCMessage()
    m.address = oscAddress

    for x in dataArray:
        m.append(x)

    return m.getBinary()



################################ receive osc from The Other.

class OSCServer(Thread) :
    def __init__(self, ipAddr='127.0.0.1', port = 9001) :
        Thread.__init__(self)
        self.ipAddr = ipAddr
        self.port = port
        self.isRunning = True

    def run(self):
        self.haveSocket = False
        # create socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # fix trouble if python leave without cleaning well the socket
        # not needed under windows, he can reuse addr even if the socket
        # are in fin2 or wait state.
        if os.name in ['posix', 'mac'] and hasattr(socket, 'SO_REUSEADDR'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # try to bind the socket, retry if necessary
        while not self.haveSocket and self.isRunning:
            try :
                self.socket.bind((self.ipAddr, self.port))
                self.socket.settimeout(0.5)
                self.haveSocket = True

            except socket.error, e:
                error, message = e.args

                # special handle for EADDRINUSE
                if error == errno.EADDRINUSE:
                    pymt_logger.error('Address %s:%i already in use, retry in 2 second' % (self.ipAddr, self.port))
                else:
                    pymt_logger.exception(e)
                self.haveSocket = False

                # sleep 2 second before retry
                time.sleep(2)

        pymt_logger.info('listening for Tuio on %s:%i' % (self.ipAddr, self.port))

        while self.isRunning:
            try:
                addressManager.handle(self.socket.recv(1024))
            except Exception, e:
                if type(e) == socket.timeout:
                    continue
                pymt_logger.error('Error in Tuio recv()')
                pymt_logger.exception(e)
                return 'no data arrived'

def listen(ipAddr='127.0.0.1', port = 9001):
    '''Creates a new thread listening to that port
    defaults to ipAddr='127.0.0.1', port 9001
    '''
    global oscThreads
    id = '%s:%d' % (ipAddr, port)
    if id in oscThreads:
        return
    print 'Add thread', id
    oscThreads[id] = OSCServer(ipAddr, port)
    oscThreads[id].start()
    return id


def dontListen(id = None):
    '''closes the socket and kills the thread
    '''
    global oscThreads
    if id and id in oscThreads:
        ids = [id]
    else:
        ids = oscThreads.keys()
    for id in ids:
        print 'Close thread', id
        oscThreads[id].socket.close()
        oscThreads[id].isRunning = 0
        del oscThreads[id]

if __name__ == '__main__':
    # example of how to use oscAPI
    init()
    listen() # defaults to "127.0.0.1", 9001
    import time
    time.sleep(5)

    # add addresses to callback manager
    def printStuff(msg):
        '''deals with "print" tagged OSC addresses
        '''
        print "printing in the printStuff function ", msg
        print "the oscaddress is ", msg[0]
        print "the value is ", msg[2]

    bind(printStuff, "/test")

    #send normal msg, two ways
    sendMsg("/test", [1, 2, 3], "127.0.0.1", 9000)
    sendMsg("/test2", [1, 2, 3]) # defaults to "127.0.0.1", 9000
    sendMsg("/hello") # defaults to [], "127.0.0.1", 9000

    # create and send bundle, to ways to send
    bundle = createBundle()
    appendToBundle(bundle, "/testing/bundles", [1, 2, 3])
    appendToBundle(bundle, "/testing/bundles", [4, 5, 6])
    sendBundle(bundle, "127.0.0.1", 9000)
    sendBundle(bundle) # defaults to "127.0.0.1", 9000

    dontListen()  # finally close the connection bfore exiting or program

