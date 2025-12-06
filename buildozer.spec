[app]
title = Robot-Tech
package.name = robottech
package.domain = org.example
source.dir = client
source.main = main.py
requirements = python3,kivy,kivymd,plyer,httpx,reportlab
android.permissions = CAMERA,INTERNET,RECORD_AUDIO
android.minapi = 29
android.sdk = 33
android.arch = armeabi-v7a,arm64-v8a
android.accept_sdk_license = True
android.add_src = client/assets
fullscreen = 0

[buildozer]
log_level = 2