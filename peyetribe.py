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
__version__ = "0.3"
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

    etm_calib = '{ "category": "calibration", "request" : "start", "values": { "pointcount": %d } }'
    etm_calib_abort = '{ "category": "calibration", "request" : "abort" }'
    etm_calib_clear = '{ "category": "calibration", "request" : "clear" }'
    etm_cpstart = '{ "category": "calibration", "request" : "pointstart", "values": { "x": %d,  "y": %d } }'
    etm_cpend = '{ "category": "calibration", "request" : "pointend" }'

    etm_get_screenres = '{ "category": "tracker", "request" : "get", "values": [ "screenresw", "screenresh" ] }'

    etm_set_push = '{ "category": "tracker", "request" : "set", "values": { "push": true } }'
    etm_set_pull = '{ "category": "tracker", "request" : "set", "values": { "push": false } }'

    etm_get_frame = '{ "category": "tracker", "request" : "get", "values": [ "frame" ] }'

    etm_heartbeat = '{ "category": "heartbeat" }'

    etm_buffer_size = 4096

    class Coord():

        """Single (x,y) positions relative to screen or bounding box. Used in Frame and Calibration."""

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

        def __str__(self):
            return (self._fmt + "%s" + self._fmt) % (self._x, self._ssep, self._y)

    class Frame():

        """
        Holds a complete decoded frame from the eye tracker.

        Access members via accessor functions or convert to string via str(...)
        """

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

            def __str__(self):
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
            self._raw = EyeTribe.Coord(json['raw']['x'], json['raw']['y'])
            self._avg = EyeTribe.Coord(json['avg']['x'], json['avg']['y'])
            eye = json['lefteye']
            self._lefteye = EyeTribe.Frame.Eye(
                EyeTribe.Coord(eye['raw']['x'], eye['raw']['y']),
                EyeTribe.Coord(eye['avg']['x'], eye['avg']['y']),
                eye['psize'],
                EyeTribe.Coord(eye['pcenter']['x'], eye['pcenter']['y'], fmt="%.3f")
            )
            eye = json['righteye']
            self._righteye = EyeTribe.Frame.Eye(
                EyeTribe.Coord(eye['raw']['x'], eye['raw']['y']),
                EyeTribe.Coord(eye['avg']['x'], eye['avg']['y']),
                eye['psize'],
                EyeTribe.Coord(eye['pcenter']['x'], eye['pcenter']['y'], fmt="%.3f")
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

        def __str__(self):
            # header = "eT;dT;aT;Fix;State;Rwx;Rwy;Avx;Avy;LRwx;LRwy;LAvx;LAvy;LPSz;LCx;LCy;RRwx;RRwy;RAvx;RAvy;RPSz;RCx;RCy"

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

    class Calibration():
        def __init__(self):
            self.result = False
            self.deg = None
            self.degl = None
            self.degr = None
            self.pointcount = 0
            self.points = None

    class CalibrationPoint():
        def __init__(self):
            self.state = -1
            self.cp = EyeTribe.Coord()
            self.mecp = EyeTribe.Coord()
            self.ad = None
            self.adl = None
            self.adr = None
            self.mep = None
            self.mepl = None
            self.mepr = None
            self.asd = None
            self.asdl = None
            self.asdr = None

    def __init__(self, host='localhost', port=6555, ssep=';', screenindex=0):
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
        self._screenindex = screenindex
        self._calibres = EyeTribe.Calibration()

    def _tell_tracker(self, message):
        """
        Send the (canned) message to the tracker and return the reply properly parsed.

        Raises an exception if we get an error message back from the tracker or if in pushmode
        """
        if self._ispushmode:
            raise Exception("Whoa, cannot send/recieve this message while in push mode: %s", message)

        self._sock.send(message.encode())
        r = self._sock.recv(EyeTribe.etm_buffer_size)
        print("-> %s" % message)
        print("<- %s" % r)
        # Note: We MAY get multiple replies here from a calibration...
        reply = None
        for js in r.decode().split("\n"):   # This will also return some empty lines sometimes...
            if js.strip() != "":
                p = json.loads(js)
                sc = p['statuscode']
                if p['category'] == 'calibration' and sc == 800:
                    pass
                elif sc != 200:
                    raise Exception("Tracker protocol error (%d) on message '%s'" % (sc, message))

                if reply is None:
                    reply = p

        return reply

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
            self._sock.settimeout(30)

            try:
                p = self._tell_tracker(EyeTribe.etm_get_init)

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

        if callback!=None:
            self._pmcallback = callback

        # set eye tracker to push mode and read it's reply (only one, we hope)
        # TODO: The eye tracker behaviour is not clear here; race conditions could appear
        self._tell_tracker(EyeTribe.etm_set_push)

        self._ispushmode = True

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
            p = self._tell_tracker(EyeTribe.etm_get_frame)

            return EyeTribe.Frame(p['values']['frame'])

    def get_screen_res(self):
        p = self._tell_tracker(EyeTribe.etm_get_screenres)

        maxx = p['values']['screenresw']
        maxy = p['values']['screenresh']

        return (maxx, maxy)

    def calibration_start(self, pointcount=9):
        """
        (Re)run the calibration procedure with pointcount points.

        Call calibration_point_start and calibration_point_end for each point when it displays on the screen.

        The result can be retrieved by latest_calibration_result after the calibration has completed.
        """

        self._tell_tracker(EyeTribe.etm_calib % pointcount)


    def calibration_point_start(self, x, y):
            self._tell_tracker(EyeTribe.etm_cpstart % (x, y))

    def calibration_point_end(self):
            p = self._tell_tracker(EyeTribe.etm_cpend)

            if 'values' in p:
                self._calibres.result = p['values']['calibresult']['result']
                self._calibres.deg = p['values']['calibresult']['deg']
                self._calibres.degl = p['values']['calibresult']['degl']
                self._calibres.degr = p['values']['calibresult']['degr']

                cps = p['values']['calibresult']['calibpoints']
                self._calibres.points = [ EyeTribe.CalibrationPoint() for i in range(len(cps)) ]
                for i in range(len(cps)):
                    self._calibres.points[i].state = cps[i]['state']
                    self._calibres.points[i].cp = EyeTribe.Coord(cps[i]['cp']['x'], cps[i]['cp']['y'])
                    self._calibres.points[i].mecp = EyeTribe.Coord(cps[i]['cp']['x'], cps[i]['cp']['y'])
                    self._calibres.points[i].ad = cps[i]['acd']['ad']
                    self._calibres.points[i].adl = cps[i]['acd']['adl']
                    self._calibres.points[i].adr = cps[i]['acd']['adr']
                    self._calibres.points[i].mep = cps[i]['mepix']['mep']
                    self._calibres.points[i].mepl = cps[i]['mepix']['mepl']
                    self._calibres.points[i].mepr = cps[i]['mepix']['mepr']
                    self._calibres.points[i].asd = cps[i]['asdp']['asd']
                    self._calibres.points[i].asdl = cps[i]['asdp']['asdl']
                    self._calibres.points[i].asdr = cps[i]['asdp']['asdr']

                if self._calibres.result:
                    print("NOTICE: Tracker calibrated succesfully, average error is %0.1f deg (L: %0.1f, R: %0.1f)" % 
                            (self._calibres.deg, self._calibres.degl, self._calibres.degr))
                else:
                    print("WARNING: Tracker failed to calibrate")

    def calibration_abort(self):
            self._tell_tracker(EyeTribe.etm_calib_abort)

    def calibration_clear(self):
            self._tell_tracker(EyeTribe.etm_calib_clear)

    def latest_calibration_result(self):
        return self._calibres

if __name__ == "__main__":
    """
    Example usage -- this code is only executed if file is run directly
    not when imported as a module, but it shows how to use this module:

    from peyetribe import EyeTribe
    import time
    """

    tracker = EyeTribe()
    tracker.connect()

    n = tracker.next()

    print("eT;dT;aT;Fix;State;Rwx;Rwy;Avx;Avy;LRwx;LRwy;LAvx;LAvy;LPSz;LCx;LCy;RRwx;RRwy;RAvx;RAvy;RPSz;RCx;RCy")

    tracker.pushmode()
    count = 0
    while count < 100:
        n = tracker.next()
        print(n)
        count += 1

    tracker.pullmode()

    tracker.close()

