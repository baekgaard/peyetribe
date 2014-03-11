"""
Simple python interface to the Eye Tribe eyetracker

A simple usage scenario is as follows:

    import peyetribe
    import sys

    tracker = EyeTribe()    # Create a tracker object (defaults to localhost:6555)
    tracker.connect()       # Initiate the TCP/IP connection to the tracker

    n = tracker.next()      # Default is pull mode: Just get a frame from the tracker
                            # Access e.g. current gaze x coordinate as avg = n.getavg().x

    tracker.pushmode()      # Switch to push mode

    count = 0               # Print out the next 100 gaze coordinates
    while count < 100:
        n = tracker.next()  # Gets next coordinate from queue (blocking!), now in push mode
        sys.stderr.write(str(n) + '\n')
        count += 1

    tracker.pullmode()      # End push mode

    tracker.close()         # Disconnect from tracker


Created by Per Baekgaard / pgba@dtu.dk / baekgaard@b4net.dk, March 2014

Licensed under the MIT License:

Copyright (c) 2014, Per Baekgaard, Technical University of Denmark, DTU Informatics, Cognitive Systems Section

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without
limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the
Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions
of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE
OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
__author__ = "Per Baekgaard"
__copyright__ = \
    "Copyright (c) 2014, Per Baekgaard, Technical University of Denmark, DTU Informatics, Cognitive Systems Section"
__license__ = "MIT"
__version__ = "0.1"
__email__ = "pgba@dtu.dk"
__status__ = "Alpha"

import threading
import queue
import time
import socket
import json
import sys


class EyeTribe():
    """
    Main class to handle the Eye Tracker

    Includes subclasses Frame (that holds an entire tracker frame with both-eye positions) and its
    Eye and Coord subclasses holding (single eye) data and all x,y coordinates
    """

    etm_get_init = '{ "category": "tracker", "request" : "get", "values": [ "iscalibrated", "heartbeatinterval" ] }'
    etm_set_push = '{ "category": "tracker", "request" : "set", "values": { "push": true } }'
    etm_set_pull = '{ "category": "tracker", "request" : "set", "values": { "push": false } }'
    etm_get_frame = '{ "category": "tracker", "request" : "get", "values": [ "frame" ] }'
    etm_heartbeat = '{ "category": "heartbeat" }'
    etm_buffer_size = 1024

    class Frame():
        """
        Holds a complete Frame from the eye tracker

        Access via accessor functions get... or convert to string via str(...)
        """
        class Coord():
            """Single (x,y) positions relative to screen typically"""
            def __init__(self, x=0, y=0, ssep=';'):
                self.x = x
                self.y = y
                self.ssep = ssep

            def getx(self):
                return self.x

            def gety(self):
                return self.y

            def __str__(self):
                return "%d%s%d" % (self.x, self.ssep, self.y)

        class Eye:
            """Single-eye data including gaze coordinates and pupil sizes etc"""
            def __init__(self, raw, avg, psize, pcenter, ssep=';'):
                self.raw = raw
                self.avg = avg
                self.psize = psize
                self.pcenter = pcenter
                self.ssep = ssep

            def getraw(self):
                return self.raw

            def getavg(self):
                return self.avg

            def getpsize(self):
                return self.psize

            def getcenter(self):
                return self.pcenter

            def __str__(self):
                return "%s%s%s%s%.1f%s%s" % \
                       (str(self.raw), self.ssep, str(self.avg), self.ssep, self.psize, self.ssep, str(self.pcenter))

        def __init__(self, json, ssep=';'):
            """Takes a json dictionary and creates an (unpacked) Frame object"""
            self.time = json['time']
            self.fix = json['fix']
            self.state = json['state']
            self.raw = EyeTribe.Frame.Coord(json['raw']['x'], json['raw']['y'])
            self.avg = EyeTribe.Frame.Coord(json['avg']['x'], json['avg']['y'])
            eye = json['lefteye']
            self.lefteye = EyeTribe.Frame.Eye(
                EyeTribe.Frame.Coord(eye['raw']['x'], eye['raw']['y']),
                EyeTribe.Frame.Coord(eye['avg']['x'], eye['avg']['y']),
                eye['psize'],
                EyeTribe.Frame.Coord(eye['pcenter']['x'], eye['pcenter']['y'])
            )
            eye = json['righteye']
            self.righteye = EyeTribe.Frame.Eye(
                EyeTribe.Frame.Coord(eye['raw']['x'], eye['raw']['y']),
                EyeTribe.Frame.Coord(eye['avg']['x'], eye['avg']['y']),
                eye['psize'],
                EyeTribe.Frame.Coord(eye['pcenter']['x'], eye['pcenter']['y'])
            )
            self.ssep = ssep

        def gettime(self):
            return self.time

        def getfix(self):
            return self.fix

        def getstate(self):
            return self.state

        def getavg(self):
            return self.avg

        def geteye(self, left=0):
            if left:
                return self.lefteye
            else:
                return self.righteye

        def __str__(self):
            st = 'L' if (self.state & 0x10) else '.'
            st += 'F' if (self.state & 0x08) else '.'
            st += 'P' if (self.state & 0x04) else '.'
            st += 'E' if (self.state & 0x02) else '.'
            st += 'G' if (self.state & 0x01) else '.'
            f = 'F' if self.fix else 'N'
            s = "%08.3f%s%s%s%s%s%s%s%s" % \
                (self.time/1000, self.ssep, f, self.ssep, st, self.ssep, str(self.raw), self.ssep, str(self.avg))
            s += "%s%s" % (self.ssep, str(self.lefteye))
            s += "%s%s" % (self.ssep, str(self.righteye))

            return s

    def __init__(self, host='localhost', port=6555, ssep=';'):
        self.host = host
        self.port = port
        self.sock = None
        self.queue = None
        self.ispushmode = False
        self.hbinterval = 0
        self.hbeater = None
        self.listener = None
        self.queue = queue.Queue()
        self.toffset = None
        self.ssep = ssep

    def connect(self):
        """
        Connect an EyeTribe object to the actual Eye Tracker by establishing a TCP/IP connection
        Also gets heartbeatinterval information (needed later for the call-back timing)
        """
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))

            self.sock.send(EyeTribe.etm_get_init.encode())
            r = self.sock.recv(EyeTribe.etm_buffer_size).decode()

            try:
                p = json.loads(r)

                sc = p['statuscode']
                if sc != 200:
                    raise Exception("connection failed, protocol error (%d)", sc)

                self.hbinterval = p['values']['heartbeatinterval']
            except ValueError:
                raise

        else:
            raise Exception("cannot connect an already connected socket; close it first")

    def bind(self, host='localhost', port=6555):
        """(Re)binds a non-connected Eye Tribe object to another host/port"""
        if not self.sock is None:
            self.host = host
            self.port = port
        else:
            raise Exception("cannot (re)bind a connected socket; close it first")

    def close(self):
        """Close TCP/IP connection, returning the object back to its starting condition"""
        if not self.sock.close is None:
            self.sock.close()
            self.sock = None
        else:
            raise Exception("cannot close an already closed connection")

    def pushmode(self):
        """
        Change to push mode, i.e. setup and start receiving tracking data
        requires a connected tracker that also has been calibrated

        Also resets the tracker time, so all returned frames are relative to the timing
        of the first returned frame
        """

        def hbeater():
            """sends heartbeats at the required interval, but does not read the reply"""
            while self.ispushmode:
                time.sleep(self.hbinterval/1000)
                sys.stderr.write("sending heartbeat\n")
                self.sock.send(EyeTribe.etm_heartbeat.encode())
            return

        def listener():
            """process pushed data (and heartbeat replies and other stuff returned) from the tracker in push mode"""

            while self.ispushmode:
                # Keep going until we're asked to terminate
                # TODO: Could hang, change to non-blocking recv with e.g. 2x hb interval
                # TODO: Make sure we have processed the final OK reply to change back to pull mode
                r = self.sock.recv(EyeTribe.etm_buffer_size)
                p = json.loads(r.decode())

                sc = p['statuscode']
                if sc != 200:
                    raise Exception("connection failed, protocol error (%d)", sc)

                # process replies with frames and store those to queue, discarding all other data for now
                # although we could also save other replies as needed about state etc
                if p['category'] != "heartbeat" and 'values' in p and 'frame' in p['values']:
                    f = EyeTribe.Frame(p['values']['frame'])

                    if self.toffset is None:
                        self.toffset = f.time
                    f.time -= self.toffset

                    self.queue.put(f)

        # if already in pushmode, do nothing...
        if self.ispushmode:
            return

        sys.stderr.write("switching to push mode...\n")

        self.ispushmode = True

        # set eye tracker to push mode and read it's reply
        self.sock.send(EyeTribe.etm_set_push.encode())
        r = self.sock.recv(EyeTribe.etm_buffer_size)
        p = json.loads(r.decode())
        sc = p['statuscode']
        if sc != 200:
            raise Exception("connection failed, protocol error (%d)", sc)

        # setup heart-beat generator
        if self.hbinterval != 0:
            self.hbeater = threading.Thread(target=hbeater, kwargs={})
            self.hbeater.daemon = True
            self.hbeater.start()

        # ... and listener that picks up frames (and handles the push mode)
        self.listener = threading.Thread(target=listener, kwargs={})
        self.listener.daemon = True
        self.listener.start()

        return

    def pullmode(self):
        """
        change to pull mode, i.e. prompt for next data set whenever you want one
        requires a connected tracker that also has been calibrated
        """

        if self.ispushmode:
            # Now end the pull mode - the listener thread may read the reply (when implemented...)
            sys.stderr.write("trying to stop the listener...\n")
            self.ispushmode = False     # will cause the listener to stop the eye tracker pushing
            self.sock.send(EyeTribe.etm_set_pull.encode())

        # sync for it to stop
        self.listener.join(min((self.hbinterval*2, 10)))
        if self.listener.isAlive():
            sys.stderr.write("thread did not terminate as expected\n")
        else:
            sys.stderr.write("threads ended normally\n")

        self.toffset = None

    def next(self):
        """
        returns the next (queued or pulled) dataset from the eyetracker
        """
        if self.ispushmode:
            return self.queue.get()
        else:
            self.sock.send(EyeTribe.etm_get_frame.encode())
            r = self.sock.recv(EyeTribe.etm_buffer_size).decode()

            p = json.loads(r)

            sc = p['statuscode']
            if sc != 200:
                raise Exception("connection failed, protocol error (%d)", sc)
            return EyeTribe.Frame(p['values']['frame'])


# Example usage:

sys.stderr.write("Starting up...\n")
tracker = EyeTribe()
tracker.connect()
n = tracker.next()

starttime = time.clock()
tracker.pushmode()
count = 0
while count < 100:
    n = tracker.next()
    sys.stderr.write(str(n) + '\n')
    count += 1

tracker.pullmode()

tracker.close()



