from kivymd.uix.widget import MDWidget
from kivy.graphics import Color, Line
from kivy.clock import Clock
import math

class RetroOsc(MDWidget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._ev = Clock.schedule_interval(self.update, 1/30)
        self.t = 0
    def update(self, dt):
        self.t += dt
        with self.canvas:
            self.canvas.clear()
            Color(0,1,0)
            pts=[]
            for x in range(0, int(self.width)):
                y = self.center_y + 50*math.sin((x/40.0)+self.t)
                pts.extend([x,y])
            Line(points=pts, width=1.2)