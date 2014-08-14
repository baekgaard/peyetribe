"""
Simple python interface to the Eye Tribe eye tracker (http://theeyetribe.com)

A simple usage scenario is as follows:

    from peyetribe import eyetribe
    import time

    tracker = eyetribe()
    tracker.connect()
    n = tracker.next()

    print("eT;dT;aT;Fix;State;Rwx;Rwy;Avx;Avy;LRwx;LRwy;LAvx;LAvy;RSz;LCx;LCy;RRwx;RRwy;RAvx;RAvy;RS;RCx;RCy\n")

    tracker.pushmode()
    count = 0
    while count < 100:
        n = tracker.next()
        print(str(n))
        count += 1

    tracker.pullmode()

    tracker.close()

To use, import the eyetribe from the peyetribe module.

Then create the tracker object and connect it. Data can then polled by calling tracker.next() repeatedly,
or you can switch to pushmode by calling tracker.pushmode() and then continue retrieving data with 
tracker.next(). When in pushmode, frames are stored on an internal queue and you're certain (almost) to
receive a non-interrupted stream from the tracker according to the interval it runs at.

When done switch out of pushmode by calling tracker.pullmode() and then finally tracker.close().

When creating the tracker object, you can specify an alternative host or port as follows:

    tracker = eyetribe(host="your.host.name", port=1234)

This module works with both Python 2 and Python 3.


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
__version__ = "0.2"
__email__ = "pgba@dtu.dk"
__status__ = "Alpha"

import sys

if sys.version_info[0] == 2:
    import Queue as q
else:
    import queue as q

import threading
import time
import socket
import json


class eyetribe():
    """
    Main class to handle the Eye Tracker

    Includes subclasses frame (that holds an entire tracker frame with both-eye positions) and its
    eye and coord subclasses holding (single eye) data and all x,y coordinates
    """

    etm_get_init = '{ "category": "tracker", "request" : "get", "values": [ "iscalibrated", "heartbeatinterval" ] }'
    etm_set_push = '{ "category": "tracker", "request" : "set", "values": { "push": true } }'
    etm_set_pull = '{ "category": "tracker", "request" : "set", "values": { "push": false } }'
    etm_get_frame = '{ "category": "tracker", "request" : "get", "values": [ "frame" ] }'
    etm_heartbeat = '{ "category": "heartbeat" }'
    etm_buffer_size = 4096

    class frame():
        """
        Holds a complete frame from the eye tracker

        Access via accessor functions get... or convert to string via str(...)
        """
        class coord():
            """Single (x,y) positions relative to screen typically"""
            def __init__(self, x=0, y=0, ssep=';', fmt="%d"):
                self.x = x
                self.y = y
                self.ssep = ssep
                self.fmt = fmt

            def getx(self):
                return self.x

            def gety(self):
                return self.y

            def __str__(self):
                return (self.fmt + "%s" + self.fmt) % (self.x, self.ssep, self.y)

        class eye:
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
            """Takes a json dictionary and creates an (unpacked) frame object"""
            self.etime = time.time()
            self.time = json['time'] / 1000.0
            self.timestamp = json['timestamp']
            self.fix = json['fix']
            self.state = json['state']
            self.raw = eyetribe.frame.coord(json['raw']['x'], json['raw']['y'])
            self.avg = eyetribe.frame.coord(json['avg']['x'], json['avg']['y'])
            eye = json['lefteye']
            self.lefteye = eyetribe.frame.eye(
                eyetribe.frame.coord(eye['raw']['x'], eye['raw']['y']),
                eyetribe.frame.coord(eye['avg']['x'], eye['avg']['y']),
                eye['psize'],
                eyetribe.frame.coord(eye['pcenter']['x'], eye['pcenter']['y'], fmt="%.3f")
            )
            eye = json['righteye']
            self.righteye = eyetribe.frame.eye(
                eyetribe.frame.coord(eye['raw']['x'], eye['raw']['y']),
                eyetribe.frame.coord(eye['avg']['x'], eye['avg']['y']),
                eye['psize'],
                eyetribe.frame.coord(eye['pcenter']['x'], eye['pcenter']['y'], fmt="%.3f")
            )
            self.ssep = ssep

        def getetime(self):
            return self.etime

        def gettime(self):
            return self.time

        def gettimestamp(self):
            return self.timestamp

        def getfix(self):
            return self.fix

        def getstate(self):
            return self.state

        def getavg(self):
            return self.avg

        def geteye(self, left=False):
            if left:
                return self.lefteye
            else:
                return self.righteye

        def __str__(self):
            # header = "eT;dT;aT;Fix;State;Rwx;Rwy;Avx;Avy;LRwx;LRwy;LAvx;LAvy;RSz;LCx;LCy;RRwx;RRwy;RAvx;RAvy;RS;RCx;RCy"
            st = 'L' if (self.state & 0x10) else '.'
            st += 'F' if (self.state & 0x08) else '.'
            st += 'P' if (self.state & 0x04) else '.'
            st += 'E' if (self.state & 0x02) else '.'
            st += 'G' if (self.state & 0x01) else '.'
            f = 'F' if self.fix else 'N'
            s = "%014.3f%s%010.3f%s%s%s" % (self.etime, self.ssep, self.time, self.ssep, self.timestamp, self.ssep,)
            s += "%s%s%s%s%s%s%s" % (f, self.ssep, st, self.ssep, str(self.raw), self.ssep, str(self.avg))
            s += "%s%s" % (self.ssep, str(self.lefteye))
            s += "%s%s" % (self.ssep, str(self.righteye))

            return s

    def __init__(self, host='localhost', port=6555, ssep=';'):
        self.host = host
        self.port = port
        self.sock = None
        self.queue = None
        self.ispushmode = False
        self.hbinterval = 0 # Note: this is (converted to a value in) seconds
        self.hbeater = None
        self.listener = None
        self.queue = q.Queue()
        self.toffset = None
        self.ssep = ssep

    def connect(self):
        """
        Connect an eyetribe object to the actual Eye Tracker by establishing a TCP/IP connection
        Also gets heartbeatinterval information, which is needed later for the call-back timing
        and also to set up sensible timeout values on the socket (if non-zero, otherwise 30s is used)

        As this is a new connection, there can be nothing "pending" in the socket stream
        and we thus don't have to care about reading more than one reply
        """
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))

            self.sock.send(eyetribe.etm_get_init.encode())
            self.sock.settimeout(30)
            r = self.sock.recv(eyetribe.etm_buffer_size).decode()

            try:
                p = json.loads(r)

                sc = p['statuscode']
                if sc != 200:
                    raise Exception("connection failed, protocol error (%d)", sc)

                self.hbinterval = int(p['values']['heartbeatinterval']) / 1000.0
                if self.hbinterval != 0:
                    self.sock.settimeout(self.hbinterval*2)
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

        This also contains the threaded functions to handle callback and listener operations
        """

        def hbeater():
            """sends heartbeats at the required interval, but does not read the reply"""
            while self.ispushmode:
                self.sock.send(eyetribe.etm_heartbeat.encode())
                # sys.stderr.write("sending heartbeat\n")
                time.sleep(self.hbinterval)
            # sys.stderr.write("normal termination of heartbeater\n")
            return

        def listener():
            """process pushed data (and heartbeat replies and other stuff returned) from the tracker in push mode"""

            while self.ispushmode:
                # Keep going until we're asked to terminate (or we timeout with an error)
                # TODO: Make sure we have processed the final OK reply to change back to pull mode
                # but the tracker does not guarantee that it doens't send another coordinate to us,
                # so it isn't really so important here to clean the queue as it will happen later
                # as/if needed
                try:
                    r = self.sock.recv(eyetribe.etm_buffer_size)

                    # Handle multiple 'frames' (but TODO: not currently split frames), somehow assuming the 
                    # non-documented newline being sent from the tracker as it currently does
                    for js in r.decode().split("\n"):   # This will also return some empty lines sometimes...
                        if js.strip() != "":
                            f = json.loads(js)
                            # check for any errors, and bail out if we get one!
                            sc = f['statuscode']
                            if sc != 200:
                                self.ispushmode = False
                                raise Exception("connection failed, protocol error (%d)", sc)

                            # process replies with frames and store those to queue, discarding all other data for now
                            # although we could also save other replies as needed about state etc
                            if f['category'] != "heartbeat" and 'values' in f and 'frame' in f['values']:
                                f = eyetribe.frame(f['values']['frame'])

                                if self.toffset is None:
                                    self.toffset = f.time
                                f.time -= self.toffset

                                self.queue.put(f)
                            # else:
                                # sys.stderr.write("Got reply on %s from tracker\n" % f['category'])
                                # sys.stderr.write("%s\n" % js)

                except socket.timeout:

                    # if the final "OK" message didn't get to us, then we're OK; otherwise complain
                    # sys.stderr.write("timeout on listener thread\n")
                    if self.ispushmode:
                        self.ispushmode = False
                        raise Exception("The pushmode connection failed with a timeout; lost tracker connection?")

            # sys.stderr.write("(normal?) termination of listener\n")

        # if already in pushmode, do nothing...
        if self.ispushmode:
            return

        # sys.stderr.write("switching to push mode...\n")

        self.ispushmode = True

        # set eye tracker to push mode and read it's reply (only one, we hope)
        # TODO: The eye tracker behaviour is not clear here; race conditions could appear
        self.sock.send(eyetribe.etm_set_push.encode())
        r = self.sock.recv(eyetribe.etm_buffer_size)
        p = json.loads(r.decode())
        sc = p['statuscode']
        if sc != 200:
            raise Exception("The connection failed with tracker protocol error (%d)", sc)

        # setup heart-beat generator
        if self.hbinterval != 0:
            self.hbeater = threading.Thread(target=hbeater, kwargs={})
            self.hbeater.daemon = True
            self.hbeater.start()
        else:
            self.hbeater = None

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
            # End the pull mode - the listener thread will read the reply
            # sys.stderr.write("trying to stop the listener and heartbeater...\n")
            self.ispushmode = False     # will cause the listener/hbeater to stop the eye tracker pushing
            self.sock.send(eyetribe.etm_set_pull.encode())

            # sync for it to stop
            self.listener.join(min((self.hbinterval*2, 10)))
            # sys.stderr.write("listener stopped...\n")
            if self.listener.isAlive():
                raise Exception("Listener thread did not terminate as expected; protocol error?")
            self.listener = None

            if self.hbinterval != 0:
                self.hbeater.join(min((self.hbinterval*2, 10)))
                # sys.stderr.write("listener stopped...\n")
                if self.hbeater.isAlive():
                    raise Exception("HeartBeater thread did not terminate as expected; protocol error?")
                self.hbeater = None

        self.toffset = None

    def next(self):
        """
        returns the next (queued or pulled) dataset from the eyetracker
        """
        if self.ispushmode:
            return self.queue.get()
        else:
            self.sock.send(eyetribe.etm_get_frame.encode())
            r = self.sock.recv(eyetribe.etm_buffer_size).decode()

            p = json.loads(r)

            sc = p['statuscode']
            if sc != 200:
                raise Exception("connection failed, protocol error (%d)", sc)
            return eyetribe.frame(p['values']['frame'])



if __name__ == "__main__":
    # Example usage -- this code is only executed if file is run directly
    # not when imported as a module, but it shows how to use this module:

    # from peyetribe import eyetribe
    # import time

    tracker = eyetribe()
    tracker.connect()
    n = tracker.next()

    print("eT;dT;aT;Fix;State;Rwx;Rwy;Avx;Avy;LRwx;LRwy;LAvx;LAvy;RSz;LCx;LCy;RRwx;RRwy;RAvx;RAvy;RS;RCx;RCy")

    tracker.pushmode()
    count = 0
    while count < 100:
        n = tracker.next()
        print(str(n))
        count += 1

    tracker.pullmode()

    tracker.close()

