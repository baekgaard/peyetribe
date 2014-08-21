peyetribe
=========

Simple python interface to the Eye Tribe eye tracker (http://theeyetribe.com)

A simple usage scenario is as follows:

    from peyetribe import EyeTribe
    import time

    tracker = EyeTribe()
    tracker.connect()
    n = tracker.next()

    print("eT;dT;aT;Fix;State;Rwx;Rwy;Avx;Avy;LRwx;LRwy;LAvx;LAvy;RSz;LCx;LCy;RRwx;RRwy;RAvx;RAvy;RS;RCx;RCy\n")

    tracker.pushmode()
    count = 0
    while count < 100:
        n = tracker.next()
        print(n)
        count += 1

    tracker.pullmode()

    tracker.close()

To use, import the EyeTribe from the peyetribe module.

Then create the tracker object and connect it. Data can then polled by calling tracker.next() repeatedly,
or you can switch to pushmode by calling tracker.pushmode() and then continue retrieving data with 
tracker.next(). When in pushmode, frames are stored on an internal queue and you're certain (almost) to
receive a non-interrupted stream from the tracker according to the interval it runs at.

When done switch out of pushmode by calling tracker.pullmode() and then finally tracker.close().

The tracker.pullmode optionally takes a callback argument. If specified, the callback will be called on
the listener thread with the frame as a parameter. The callback can then either dispose of the frame somehow
within the application -- in which case it should return True to indicate that the frame should not be queued.
This could alternatively be used for filtering which frames are to be queued for later processing.

When creating the tracker object, you can specify an alternative host or port as follows:

    tracker = EyeTribe(host="your.host.name", port=1234)

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
