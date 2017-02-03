pilights - Raspberry Pi + LEDs + clock
======================================
Dawn simulator alarm clock with a Raspberry Pi. 

Exposes a REST interface to control light levels.


Usage
--------------------------------------
```
sudo python pilights.py
```
(Best run from a screen session so the window doesn't close)


REST API
--------------------------------------
**GET /lights**

Returns status of lights
```
$ curl raspberrypi:8000/lights/
{"blue": 0, "white": 0, "green": 0, "red": 0}
```

**PUT /lights**

Sets levels for each light channel. Default range is 0 (off) - 80 (full)
```
$ curl -X PUT --data 'red=0&green=0&blue=0&white=0' raspberrypi:8000/lights
{"blue": 0, "white": 0, "green": 0, "red": 0}
```

**PUT /lights/ramp**

Gradually adjusts lights to the given level over the given duration in seconds. Does not return until 
light is at new level. Colors aren't currently mixed, fades channels sequentially.
```
$ curl -X PUT --data 'red=0&green=0&blue=0&white=60&duration=5' raspberrypi:8000/lights
{"blue": 0, "white": 60, "green": 0, "red": 0, "duration": 5}
```


Notes
-------------------------------------
- Does not do any kind of access control or blocking for multiple requests. You wouldn't want to
expose this to the internet.
- Uses DMA-driver pulse width modulation to dim LED strips
- Depends completely on the Raspberry Pi and how the GPIO pins are wired. Configured on the line
``` with LEDS(GPIO, 40, 38, 37, 36) as leds:```
