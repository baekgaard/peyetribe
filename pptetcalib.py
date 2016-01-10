"""
Simple PsychoPy calibration routine for the Eye Tribe eye tracker (http://theeyetribe.com)

Created by Per Baekgaard / pgba@dtu.dk / baekgaard@b4net.dk, September 2015

Licensed under the MIT License:

    Copyright (c) 2015, Per Baekgaard, Technical University of Denmark, DTU Informatics, Cognitive Systems Section

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
            "Copyright (c) 2015, Per Baekgaard, Technical University of Denmark, DTU Informatics, Cognitive Systems Section"
__license__ = "MIT"
__version__ = "0.1"
__email__ = "pgba@dtu.dk"
__status__ = "Alpha"

from psychopy import visual, core, event, monitors, tools
import pyglet
from peyetribe import EyeTribe
import math

def calibrate_tracker(win, tracker):
    '''
    Run a calibration routine on the eye tracker 'tracker' in specified 'win' (must be fullscreen)

    Returns True if the latest performed calibration is succesful, False otherwise
    '''

    def tween_pos(a, b, r):
        def quad_in_out(r):
            if r < 0.5:
                return 2 * r * r
            else:
                return 1 - (2 * (1-r) * (1-r))

        def cos_in_out(r):
            return 0.5 * (1 - math.cos(r * math.pi))

        def cos_in(r):
            return (1 - math.cos(r * math.pi/2))

        '''Return position r:[0,1] between a and b'''
        ease = cos_in

        return (b[0] - (b[0] - a[0])*(1-ease(r)), b[1] - (b[1] - a[1])*(1-ease(r)))

    def display_text(text, noWait=False, time=2):
        visual.TextStim(win, alignHoriz='center', wrapWidth=0.5, height=0.033, color='black', text=text, units='norm').draw()
        win.flip()
        if noWait:
            core.wait(time)
            win.flip()
            return None
        else:
            keys = event.waitKeys()
            win.flip()

            return keys[0]
 
    if 'escape' == display_text("Will now calibrate the eye tracker.\n" + \
                            "Please follow the presented circles.\nEnsure you fixate while they are red.\n\n" + \
                            "Press SPACE when ready for calibration"):
        return False

    maxx, maxy = tracker.get_screen_res()

    periradius = 30
    pwincolor = win.color
    recal = True
    while recal:
        win.color = '#444'

        ccent = visual.Circle(win, 4)
        cperi = visual.Circle(win, periradius)
        ccent.lineColor = None
        ccent.fillColor = "#fff"
        ccent.units = 'pix'
        ccent.colorSpace = 'rgb'
        cperi.lineColor = "#fff"
        cperi.fillColor = None
        cperi.units = 'pix'
        cperi.colorSpace = 'rgb'

        win.flip()

        tracker.calibration_start(9)
        points = []
        prx = None
        pry = None
        for n in range(9):
            i = (n + 4) % 9
            x = ((i%3)-1.0)*0.9 * maxx/2.0
            y = -((i//3)-1.0)*0.9 * maxy/2.0

            ccent.fillColor = "#fff"
            cperi.lineColor = "#fff"
            cperi.radius = periradius/2

            if prx is not None and pry is not None and (prx!=x or pry!=y):
                for twi in range(30):
                    ccent.pos = tween_pos((prx, pry), (x, y), twi/30.)
                    cperi.pos = tween_pos((prx, pry), (x, y), twi/30.)
                    win.flip()
            ccent.pos = (x, y)
            cperi.pos = (x, y)
            prx = x
            pry = y

            px = x + round(maxx/2)
            py = maxy - (y + maxy - round(maxy/2))


            ccent.autoDraw = True
            cperi.autoDraw = True

            for i in range(30):
                cperi.radius = (periradius-5)*(30-i)/30.0 + 5
                win.flip()
            for i in range(15):
                cperi.radius = (periradius-5)*i/30.0 + 5
                win.flip()

            ccent.fillColor = "#f88"
            cperi.lineColor = "#f88"
            win.flip()

            tracker.calibration_point_start(px, py)
            core.wait(1.0)
            tracker.calibration_point_end()

            ccent.fillColor = "#bfb"
            cperi.lineColor = "#bfb"
            win.flip()
            core.wait(0.5)

            points.append((x, y, px, py))

        ccent.autoDraw = False
        cperi.autoDraw = False
        del ccent
        del cperi

        win.color = pwincolor 
        win.flip()

        cres = tracker.latest_calibration_result()
        if not cres.result:
            abort = 'escape' == display_text("Your calibration failed. Press SPACE to redo.")
            tracker.calibration_abort()
            if abort:
                return False
        else:
            cpcs = []
            for cp in cres.points:
                cpc = visual.Circle(win, cp.mep)
                cpc.lineColor = None
                if cp.mep > 100:
                    cpc.fillColor = "#fbb"
                elif cp.mep > 50:
                    cpc.fillColor = "#ffb"
                else:
                    cpc.fillColor = "#bfb"
                cpc.units = 'pix'
                cpc.colorSpace = 'rgb'
                cpc.pos = (cp.cp.x - round(maxx/2), -(cp.cp.y - maxy + round(maxy)/2))
                cpc.draw()
                cpc.autoDraw = True
                cpcs.append(cpc)


            eye = visual.ShapeStim(win, fillColor=None, lineColor='black', 
                    lineWidth=1, units='pix', vertices=[[0,0], [0,15], [0,-15], [0,0], [-15,0], [15,0], [0,0]])
            eye.autoDraw = True
            eye.draw()
            
            t = visual.TextStim(win, alignHoriz='center', wrapWidth=0.5, height=0.033, color='black', units='norm',
                    text="Calibration is acceptable.\nPress SPACE to continue (or R to redo).")
            t.units = 'pix'
            t.autoDraw = True
            t.draw()

            win.flip()

            cont = True
            while cont:
                ef = tracker.next()
                eye.pos = (ef.avg.x - round(maxx/2), -(ef.avg.y - maxy + round(maxy)/2))
                eye.draw()
                win.flip()

                keys = event.getKeys()
                if keys is not None and len(keys)>0:
                    cont = False
                    recal = keys[0] == 'r'

            for cpc in cpcs:
                cpc.autoDraw = False
            eye.autoDraw = False
            t.autoDraw = False

            if recal:
                tracker.calibration_clear()

    return True
