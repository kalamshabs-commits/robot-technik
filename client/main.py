import os
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.toast import toast
from plyer import camera

KV = """
<OscScreen>:
    name: 'osc'
    MDBoxLayout:
        orientation: 'vertical'
        MDRaisedButton:
            text: 'Start'
            on_release: root.start()
        MDRaisedButton:
            text: 'Stop'
            on_release: root.stop()
        MDLabel:
            id: status
            text: ''

<MainScreen>:
    name: 'main'
    MDBoxLayout:
        orientation: 'vertical'
        MDRaisedButton:
            text: 'Oscilloscope'
            on_release: app.sm.current='osc'
        MDRaisedButton:
            text: 'Capture'
            on_release: app.capture()
"""

class OscScreen(MDScreen):
    def start(self):
        self.ids.status.text = 'running'
    def stop(self):
        self.ids.status.text = 'stopped'

class MainScreen(MDScreen):
    pass

class App(MDApp):
    def build(self):
        Builder.load_string(KV)
        from kivymd.uix.screenmanager import MDScreenManager
        self.sm = MDScreenManager()
        self.sm.add_widget(MainScreen())
        self.sm.add_widget(OscScreen())
        return self.sm
    def capture(self):
        try:
            camera.take_picture(filename='demo.jpg', on_complete=lambda: toast('captured'))
        except Exception:
            toast('camera not available')

if __name__=='__main__':
    App().run()