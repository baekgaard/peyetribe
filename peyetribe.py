"""
Simple python (2 and 3) interface to the Eye Tribe eye tracker (http://theeyetribe.com)

See README.md for instructions


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

import time
from datetime import datetime
import threading
import socket
import json


class EyeTribe():

    """
    Main class to handle the Eye Tracker interface and values.

    Includes subclasses Frame (that holds an entire tracker frame with 
    both-eye positions) and its Eye and Coord subclasses holding (single eye) 
    data and all (x,y) coordinates of eye and bounding boxes
    """

    etm_get_init = '{ "category": "tracker", "request" : "get", "values": [ "iscalibrated", "heartbeatinterval" ] }'
    etm_set_push = '{ "category": "tracker", "request" : "set", "values": { "push": true } }'
    etm_set_pull = '{ "category": "tracker", "request" : "set", "values": { "push": false } }'
    etm_get_frame = '{ "category": "tracker", "request" : "get", "values": [ "frame" ] }'
    etm_heartbeat = '{ "category": "heartbeat" }'
    etm_buffer_size = 4096

    class Frame():

        """
        Holds a complete decoded frame from the eye tracker.

        Access members via accessor functions or convert to string via str(...)
        """

        class Coord():

            """Single (x,y) positions relative to screen or bounding box."""

            def __init__(self, x=0, y=0, ssep=';', fmt="%d"):
                self._x = x
                self._y = y
                self._ssep = ssep
                self._fmt = fmt

            @property
            def x(self):
                """The horizontal cartesian offset (abcissa)."""
                return self._x

            @x.setter
            def x(self, val):
                self._x = val

            @property
            def y(self):
                """The vertical cartesian offset (ordinate)."""
                return self._y

            @y.setter
            def y(self, val):
                self._y = val

            def __repr__(self):
                return (self._fmt + "%s" + self._fmt) % (self._x, self._ssep, self._y)

        class Eye:

            """Single-eye data, including gaze coordinates and pupil size"""

            def __init__(self, raw, avg, psize, pcenter, ssep=';'):
                self._raw = raw
                self._avg = avg
                self._psize = psize
                self._pcenter = pcenter
                self._ssep = ssep

            @property
            def raw(self):
                """The raw (unfiltered) cartesian eye coordinate vs screen coordinates."""
                return self._raw

            @raw.setter
            def raw(self, val):
                self._raw = val

            @property
            def avg(self):
                """The averaged (filtered) cartesian eye coordinate vs screen coordinates."""
                return self._avg

            @avg.setter
            def avg(self, val):
                self._avg = val

            @property
            def psize(self):
                """A relative estimate of the pupil size."""
                return self._psize

            @psize.setter
            def psize(self, val):
                self._psize = val

            @property
            def pcenter(self):
                """The center coordinate of the eye within the bounding box."""
                return self._pcenter

            @pcenter.setter
            def pcenter(self, val):
                self._pcenter = val

            def __repr__(self):
                return "%s%s%s%s%.1f%s%s" % \
                       (str(self._raw), self._ssep, str(self._avg), self._ssep, self._psize, self._ssep, str(self._pcenter))

        def __init__(self, json, ssep=';'):
            """
            Creates a frame based on an unpacked version of the eye tracker json string.

            The ssep is used for separating values when the frame is converted to
            a string, as in a print statement. This is useful for dumping csv files.
            """

            self._etime = time.time()
            self._time = json['time'] / 1000.0
            ts = datetime.strptime(json['timestamp'], "%Y-%m-%d %H:%M:%S.%f")
            self._timestamp = int(ts.strftime("%s")) + int(ts.strftime("%f"))/1000000.0 
            self._fix = json['fix']
            self._state = json['state']
            self._raw = EyeTribe.Frame.Coord(json['raw']['x'], json['raw']['y'])
            self._avg = EyeTribe.Frame.Coord(json['avg']['x'], json['avg']['y'])
            eye = json['lefteye']
            self._lefteye = EyeTribe.Frame.Eye(
                EyeTribe.Frame.Coord(eye['raw']['x'], eye['raw']['y']),
                EyeTribe.Frame.Coord(eye['avg']['x'], eye['avg']['y']),
                eye['psize'],
                EyeTribe.Frame.Coord(eye['pcenter']['x'], eye['pcenter']['y'], fmt="%.3f")
            )
            eye = json['righteye']
            self._righteye = EyeTribe.Frame.Eye(
                EyeTribe.Frame.Coord(eye['raw']['x'], eye['raw']['y']),
                EyeTribe.Frame.Coord(eye['avg']['x'], eye['avg']['y']),
                eye['psize'],
                EyeTribe.Frame.Coord(eye['pcenter']['x'], eye['pcenter']['y'], fmt="%.3f")
            )
            self._ssep = ssep

        @property
        def etime(self):
            """The wall-time epoch at the point when the frame is unpacked on the client."""
            return self._etime

        @etime.setter
        def etime(self, val):
            self._etime = val

        @property
        def time(self):
            """A monotoneous clock value from the tracker."""
            return self._time

        @time.setter
        def time(self, val):
            self._time = val

        @property
        def timestamp(self):
            """The wall-time epoch at the point the eye tracker server created the frame."""
            return self._timestamp

        @timestamp.setter
        def timestamp(self, val):
            self._timestamp = val

        @property
        def fix(self):
            """The fixation flag (True or False) from the eye tracker."""
            return self._fix

        @fix.setter
        def fix(self, val):
            self._fix = val

        @property
        def state(self):
            """The state from the eye tracker (a numeric value)."""
            return self._state

        @state.setter
        def state(self, val):
            self._state = val

        @property
        def avg(self):
            """An averaged fixation coordinate based on both eyes."""
            return self._avg

        @avg.setter
        def avg(self, val):
            self._avg = val

        @property
        def raw(self):
            """The raw (unfiltered) fixation coordinate based on both eyes."""
            return self._raw

        @raw.setter
        def raw(self, val):
            self._raw = val

        @property
        def lefteye(self):
            """Left eye coordinates, pupil position and size."""
            return self._lefteye

        @lefteye.setter
        def lefteye(self, val):
            self._lefteye = val

        @property
        def righteye(self):
            """Right eye coordinates, pupil position and size."""
            return self._righteye

        @righteye.setter
        def righteye(self, val):
            self._righteye = val

        def eye(self, left=False):
            if left:
                return self._lefteye
            else:
                return self._righteye

        def __repr__(self):
            # header = "eT;dT;aT;Fix;State;Rwx;Rwy;Avx;Avy;LRwx;LRwy;LAvx;LAvy;RSz;LCx;LCy;RRwx;RRwy;RAvx;RAvy;RS;RCx;RCy"

            st = 'L' if (self._state & 0x10) else '.'
            st += 'F' if (self._state & 0x08) else '.'
            st += 'P' if (self._state & 0x04) else '.'
            st += 'E' if (self._state & 0x02) else '.'
            st += 'G' if (self._state & 0x01) else '.'
            f = 'F' if self._fix else 'N'
            s = "%014.3f%s%07.3f%s%07.3f%s" % (self._etime, self._ssep, self._time, self._ssep, self._timestamp, self._ssep,)
            s += "%s%s%s%s%s%s%s" % (f, self._ssep, st, self._ssep, str(self._raw), self._ssep, str(self._avg))
            s += "%s%s" % (self._ssep, str(self._lefteye))
            s += "%s%s" % (self._ssep, str(self._righteye))

            return s

    def __init__(self, host='localhost', port=6555, ssep=';'):
        """
        Create an EyeTribe connection object that can be used to connect to an eye tracker.

        Parameters host and port are the values to use when connecting to the tracker.
        The ssep can be used to specify an alternative value for value separators when
        printing out a value.
        """
        self._host = host
        self._port = port
        self._sock = None
        self._queue = None
        self._ispushmode = False
        self._hbinterval = 0 # Note: this is (converted to a value in) seconds
        self._hbeater = None
        self._listener = None
        self._queue = q.Queue()
        self._pmcallback = None
        self._toffset = None
        self._ssep = ssep

    def connect(self):
        """
        Connect an eyetribe object to the actual Eye Tracker by establishing a TCP/IP connection.

        Also gets heartbeatinterval information, which is needed later for the call-back timing
        and to set up sensible timeout values on the socket (if non-zero, otherwise 30s is used)

        As this is a new connection, there can be nothing "pending" in the socket stream
        and we thus don't have to care about reading more than one reply
        """

        if self._sock is None:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.connect((self._host, self._port))

            self._sock.send(EyeTribe.etm_get_init.encode())
            self._sock.settimeout(30)
            r = self._sock.recv(EyeTribe.etm_buffer_size).decode()

            try:
                p = json.loads(r)

                sc = p['statuscode']
                if sc != 200:
                    raise Exception("connection failed, protocol error (%d)", sc)

                self._hbinterval = int(p['values']['heartbeatinterval']) / 1000.0
                if self._hbinterval != 0:
                    self._sock.settimeout(self._hbinterval*2)
            except ValueError:
                raise

        else:
            raise Exception("cannot connect an already connected socket; close it first")

    def bind(self, host='localhost', port=6555):
        """(Re)binds a non-connected Eye Tribe object to another host/port."""
        if not self._sock is None:
            self._host = host
            self._port = port
        else:
            raise Exception("cannot (re)bind a connected socket; close it first")

    def close(self):
        """Close TCP/IP connection, returning the object back to its starting condition."""
        if not self._sock.close is None:
            self._sock.close()
            self._sock = None
        else:
            raise Exception("cannot close an already closed connection")

    def pushmode(self, callback=None):
        """
        Change to push mode, i.e. setup and start receiving tracking data

        Requires a connected tracker that also has been calibrated

        If callback is not given, frames are just stored to the queue and can be retrieved with 
        the next() operation; otherwise the callback is invoked with the new frame as parameter. 
        The callback can return True to indicate that no further processing should be done
        on the frame; otherwise the frame will be queued as normal for later retrieval by next().

        Note that the callback is called on the listener thread!

        This function also contains the threaded functions handling callback and listener operations

        """

        def hbeater():
            """sends heartbeats at the required interval, but does not read the reply."""

            while self._ispushmode:
                self._sock.send(EyeTribe.etm_heartbeat.encode())
                # sys.stderr.write("sending heartbeat\n")
                time.sleep(self._hbinterval)
            # sys.stderr.write("normal termination of heartbeater\n")
            return

        def listener():
            """process pushed data (and heartbeat replies and other stuff returned) from the tracker in push mode."""

            while self._ispushmode:
                # Keep going until we're asked to terminate (or we timeout with an error)
                try:
                    r = self._sock.recv(EyeTribe.etm_buffer_size)

                    # Handle multiple 'frames' (but TODO: not currently split frames), somehow assuming the 
                    # non-documented newline being sent from the tracker as it currently does
                    for js in r.decode().split("\n"):   # This will also return some empty lines sometimes...
                        if js.strip() != "":
                            f = json.loads(js)
                            # check for any errors, and bail out if we get one!
                            sc = f['statuscode']
                            if sc != 200:
                                self._ispushmode = False
                                raise Exception("connection failed, protocol error (%d)", sc)

                            # process replies with frames and store those to queue, discarding all other data for now
                            # although we could also save other replies as needed about state etc
                            if f['category'] != "heartbeat" and 'values' in f and 'frame' in f['values']:
                                f = EyeTribe.Frame(f['values']['frame'])

                                if self._toffset is None:
                                    self._toffset = f.time
                                # f.time -= self._toffset

                                if self._pmcallback != None:
                                    dont_queue = self._pmcallback(f)
                                else:
                                    dont_queue = False

                                if not dont_queue:
                                    self._queue.put(f)
                            # else:
                                # sys.stderr.write("Got reply on %s from tracker\n" % f['category'])
                                # sys.stderr.write("%s\n" % js)

                except socket.timeout:

                    # The final "OK" message didn't get to us, but we're still OK; otherwise complain
                    # sys.stderr.write("timeout on listener thread\n")
                    if self._ispushmode:
                        self._ispushmode = False
                        raise Exception("The pushmode connection failed with a timeout; lost tracker connection?")

            # sys.stderr.write("(normal?) termination of listener\n")

        # if already in pushmode, do nothing...
        if self._ispushmode:
            return

        # sys.stderr.write("switching to push mode...\n")

        self._ispushmode = True
        if callback!=None:
            self._pmcallback = callback

        # set eye tracker to push mode and read it's reply (only one, we hope)
        # TODO: The eye tracker behaviour is not clear here; race conditions could appear
        self._sock.send(EyeTribe.etm_set_push.encode())
        r = self._sock.recv(EyeTribe.etm_buffer_size)
        p = json.loads(r.decode())
        sc = p['statuscode']
        if sc != 200:
            raise Exception("The connection failed with tracker protocol error (%d)", sc)

        # setup heart-beat generator
        if self._hbinterval != 0:
            self._hbeater = threading.Thread(target=hbeater, kwargs={})
            self._hbeater.daemon = True
            self._hbeater.start()
        else:
            self._hbeater = None

        # ... and listener that picks up frames (and handles the push mode)
        self._listener = threading.Thread(target=listener, kwargs={})
        self._listener.daemon = True
        self._listener.start()

        return

    def pullmode(self):
        """
        Change to pull mode, i.e. prompt by calling next() whenever you pull for a frame.

        Requires a connected tracker that also has been calibrated
        """

        if self._ispushmode:
            # End the pull mode - the listener thread will read the reply
            # sys.stderr.write("trying to stop the listener and heartbeater...\n")
            self._ispushmode = False     # will cause the listener/hbeater to stop the eye tracker pushing
            self._sock.send(EyeTribe.etm_set_pull.encode())

            # sync for it to stop
            self._listener.join(min((self._hbinterval*2, 10)))
            # sys.stderr.write("listener stopped...\n")
            if self._listener.isAlive():
                raise Exception("Listener thread did not terminate as expected; protocol error?")
            self._listener = None

            if self._hbinterval != 0:
                self._hbeater.join(min((self._hbinterval*2, 10)))
                # sys.stderr.write("listener stopped...\n")
                if self._hbeater.isAlive():
                    raise Exception("HeartBeater thread did not terminate as expected; protocol error?")
                self._hbeater = None

        self._toffset = None
        self._pmcallback = None

    def next(self, block=True):
        """
        Returns the next (queued or pulled) dataset from the eyetracker.

        If block is False, and we're in pushmode and the queue is empty, None is returned immediatedly, 
        otherwise we will wait for the next frame to arrive and return that
        """
        if self._ispushmode:
            try:
                return self._queue.get(block)
            except q.Empty:
                return None
        else:
            self._sock.send(EyeTribe.etm_get_frame.encode())
            r = self._sock.recv(EyeTribe.etm_buffer_size).decode()

            p = json.loads(r)

            sc = p['statuscode']
            if sc != 200:
                raise Exception("connection failed, protocol error (%d)", sc)
            return EyeTribe.Frame(p['values']['frame'])



if __name__ == "__main__":
    """
    Example usage -- this code is only executed if file is run directly
    not when imported as a module, but it shows how to use this module:

    from peyetribe import eyetribe
    import time
    """

    tracker = EyeTribe()
    tracker.connect()
    n = tracker.next()

    print("eT;dT;aT;Fix;State;Rwx;Rwy;Avx;Avy;LRwx;LRwy;LAvx;LAvy;RSz;LCx;LCy;RRwx;RRwy;RAvx;RAvy;RS;RCx;RCy")

    tracker.pushmode()
    count = 0
    while count < 100:
        n = tracker.next()
        print(n)
        count += 1

    tracker.pullmode()

    tracker.close()

