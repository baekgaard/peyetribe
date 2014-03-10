"""
Simple python interface to the Eye Tribe eyetracker
"""
import threading
import queue
import time
import socket
import json
import sys


class EyeTribe():
    """
    connect to and get date from the eye tribe eye tracker
    """

    etm_get_init = '{ "category": "tracker", "request" : "get", "values": [ "iscalibrated", "heartbeatinterval" ] }'
    etm_set_push = '{ "category": "tracker", "request" : "set", "values": { "push": true } }'
    etm_set_pull = '{ "category": "tracker", "request" : "set", "values": { "push": false } }'
    etm_get_frame = '{ "category": "tracker", "request" : "get", "values": [ "frame" ] }'
    etm_heartbeat = '{ "category": "heartbeat" }'
    etm_buffer_size = 1024

    class Frame():
        class Pos():
            def __init__(self, x=0, y=0):
                self.x = x
                self.y = y

            def getx(self):
                return self.x

            def gety(self):
                return self.y

            def marshall(self, sep=';'):
                return "%d%s%d" % (self.x, sep, self.y)

        class Eye:
            def __init__(self, raw, avg, psize, pcenter):
                self.raw = raw
                self.avg = avg
                self.psize = psize
                self.pcenter = pcenter

            def getraw(self):
                return self.raw

            def getavg(self):
                return self.avg

            def getpsize(self):
                return self.psize

            def getcenter(self):
                return self.pcenter

            def marshall(self, sep=';'):
                return "%s%s%s%s%.1f%s%s" % (self.raw.marshall(sep),sep,self.avg.marshall(sep),sep,self.psize,sep,self.pcenter.marshall(sep))

        def __init__(self, json):
            self.time = json['time']
            self.fix = json['fix']
            self.state = json['state']
            self.raw = EyeTribe.Frame.Pos(json['raw']['x'], json['raw']['y'])
            self.avg = EyeTribe.Frame.Pos(json['avg']['x'], json['avg']['y'])
            eye = json['lefteye']
            self.lefteye = EyeTribe.Frame.Eye(
                EyeTribe.Frame.Pos(eye['raw']['x'], eye['raw']['y']),
                EyeTribe.Frame.Pos(eye['avg']['x'], eye['avg']['y']),
                eye['psize'],
                EyeTribe.Frame.Pos(eye['pcenter']['x'], eye['pcenter']['y'])
            )
            eye = json['righteye']
            self.righteye = EyeTribe.Frame.Eye(
                EyeTribe.Frame.Pos(eye['raw']['x'], eye['raw']['y']),
                EyeTribe.Frame.Pos(eye['avg']['x'], eye['avg']['y']),
                eye['psize'],
                EyeTribe.Frame.Pos(eye['pcenter']['x'], eye['pcenter']['y'])
            )

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

        def marshall(self, sep=';'):
            st = 'L' if (self.state & 0x10) else '.'
            st += 'F' if (self.state & 0x08) else '.'
            st += 'P' if (self.state & 0x04) else '.'
            st += 'E' if (self.state & 0x02) else '.'
            st += 'G' if (self.state & 0x01) else '.'
            f = 'F' if (self.fix) else 'N'
            s = "%08.3f%s%s%s%s%s%s%s%s" % (self.time/1000, sep, f, sep, st, sep, self.raw.marshall(sep), sep, self.avg.marshall(sep))
            s += "%s%s" % (sep, self.lefteye.marshall(sep))
            s += "%s%s" % (sep, self.righteye.marshall(sep))

            return s

    def __init__(self, host='localhost', port=6555):
        self.host = host
        self.port = port
        self.sock = None
        self.queue = None
        self.ispushmode = False
        self.hbinterval = 0
        self.hbeater = None
        self.puller = None
        self.queue = queue.Queue()
        self.toffset = None

    def connect(self):
        if self.sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))

            self.sock.send(EyeTribe.etm_get_init.encode())
            r = self.sock.recv(EyeTribe.etm_buffer_size)

            try:
                p = json.loads(r.decode())

                sc = p['statuscode']
                if sc != 200:
                    raise Exception("connection failed, protocol error (%d)", sc)

                # sys.stderr.write("iscalibrated: %s, heartbeatinterval: %s\n" % (p['values']['iscalibrated'], p['values']['heartbeatinterval']))
                self.hbinterval = p['values']['heartbeatinterval']
            except ValueError:
                raise

        else:
            raise Exception("cannot connect an already connected socket; close it first")

    def bind(self, host='localhost', port=6555):
        if not self.sock is None:
            self.host = host
            self.port = port
        else:
            raise Exception("cannot (re)bind a connected socket; close it first")

    def close(self):
        if not self.sock.close is None:
            self.sock.close()
            self.sock = None
        else:
            raise Exception("cannot close an already closed connection")

    def pushmode(self):
        """
        change to push mode, i.e. setup and start receiving tracking data
        requires a connected tracker that also has been calibrated
        """

        def hbeater():
            """sends heartbeats at the required interval, but does not read the reply"""
            while self.ispushmode:
                time.sleep(self.hbinterval/1000)
                sys.stderr.write("sending heartbeat\n")
                self.sock.send(EyeTribe.etm_heartbeat.encode())
            return

        def puller():
            """process pushed data (and heartbeat replies) from the tracker in push mode"""

            while self.ispushmode:
                r = self.sock.recv(EyeTribe.etm_buffer_size)
                # sys.stderr.write("inpush raw response: %s\n" % (r))
                p = json.loads(r.decode())

                sc = p['statuscode']
                if sc != 200:
                    raise Exception("connection failed, protocol error (%d)", sc)

                # process replies with frames and store those to queue
                if p['category'] != "heartbeat" and 'values' in p and 'frame' in p['values']:
                    f = EyeTribe.Frame(p['values']['frame'])

                    if self.toffset is None:
                        self.toffset = f.time
                    f.time -= self.toffset

                    self.queue.put(f)
                    # sys.stderr.write ("[%.3f] at (%d,%d), left: (%d,%d), right: (%d,%d)\n" % (f.time/1000, f.avg.x, f.avg.y, f.lefteye.avg.x, f.lefteye.avg.y, f.righteye.avg.x, f.righteye.avg.y))

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
        self.puller = threading.Thread(target=puller, kwargs={})
        self.puller.daemon = True
        self.puller.start()

        return

    def pullmode(self):
        """
        change to pull mode, i.e. prompt for next data set whenever you want one
        requires a connected tracker that also has been calibrated
        """
        # now end the pull mode (and let the puller thread read the reply, hopefully)

        if self.ispushmode:
            sys.stderr.write("trying to stop the puller...\n")
            self.ispushmode = False     # will cause the puller to stop the eye tracker pushing
            self.sock.send(EyeTribe.etm_set_pull.encode())

        # sync for it to stop
        self.puller.join(min((self.hbinterval*2, 10)))
        if self.puller.isAlive():
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
            r = self.sock.recv(EyeTribe.etm_buffer_size)

            try:
                p = json.loads(r.decode())

                sc = p['statuscode']
                if sc != 200:
                    raise Exception("connection failed, protocol error (%d)", sc)
                return EyeTribe.Frame(p['values']['frame'])

            except ValueError:
                raise

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
    sys.stderr.write (n.marshall() + '\n')
    count += 1

tracker.pullmode()

tracker.close()



