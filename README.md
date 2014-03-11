peyetribe
=========

Simple python interface to the Eye Tribe eye tracker (http://theeyetribe.com)

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


