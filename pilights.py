#!/usr/bin/python
import falcon
import json
from wsgiref import simple_server
import RPi.GPIO as GPIO
import time
import random
import threading
import sys

#
# pilights - Raspberry Pi powered dawn simulator lamp with timer
#


class Alarm:
    """
    Starts programmed light sequence at a given time, prints time to stdout
    """
    leds = None

    def __init__(self, led_controller):
        self.leds = led_controller

    @staticmethod
    def run():
        print("Alarm clock thread starting")
        while True:
            t = time.localtime()
            print("{:02d}:{:02d}:{:02d}".format(t.tm_hour, t.tm_min, t.tm_sec))
            if t.tm_hour == 4 and t.tm_min == 45:
                print("Wake up!")
                leds.dawn()     # Blocking call, no more events until the lights finish running through the pattern
            time.sleep(1)


class Lights:
    leds = None

    def __init__(self, led_controller):
        self.leds = led_controller

    @staticmethod
    def on_get(req, resp):
        """ Gets status of lights"""
        light_levels = {'red': leds.r.level,
                        'green': leds.g.level,
                        'blue': leds.b.level,
                        'white': leds.w.level}
        resp.body = json.dumps(light_levels)

    @staticmethod
    def on_put(req, resp):
        """ Sets lights to the given level"""
        red = req.get_param_as_int("red", False, leds.r.min_level, leds.r.max_level)
        green = req.get_param_as_int("green", False, leds.g.min_level, leds.g.max_level)
        blue = req.get_param_as_int("blue", False, leds.b.min_level, leds.b.max_level)
        white = req.get_param_as_int("white", False, leds.w.min_level, leds.w.max_level)
        if red is not None:
            leds.r.set_level(red)
        if green is not None:
            leds.g.set_level(green)
        if blue is not None:
            leds.b.set_level(blue)
        if white is not None:
            leds.w.set_level(white)
        response = {'red': red, 'green': green, 'blue': blue, 'white': white}
        resp.body = json.dumps(response)


class LightsRamp:
    leds = None

    def __init__(self, led_controller):
        self.leds = led_controller

    @staticmethod
    def on_put(req, resp):
        """ Sets lights to the given level"""
        red = req.get_param_as_int("red", False, leds.r.min_level, leds.r.max_level)
        green = req.get_param_as_int("green", False, leds.g.min_level, leds.g.max_level)
        blue = req.get_param_as_int("blue", False, leds.b.min_level, leds.b.max_level)
        white = req.get_param_as_int("white", False, leds.w.min_level, leds.w.max_level)
        duration = req.get_param_as_int("duration", True, 0, 60)
        if duration is not None:
            if red is not None:
                leds.r.ramp_to(red, duration)
            if green is not None:
                leds.g.ramp_to(green, duration)
            if blue is not None:
                leds.b.ramp_to(blue, duration)
            if white is not None:
                leds.w.ramp_to(white, duration)
        response = {'duration': duration, 'red': red, 'green': green, 'blue': blue, 'white': white}
        resp.body = json.dumps(response)


class LED:
    def __init__(self, gpio, pin):
        self.gp = gpio
        self.pin = pin
        self.hertz = 60
        self.min_level = 0
        self.max_level = 80
        self.level = self.min_level

        self.gp.setup(pin, gpio.OUT)
        self.output = self.gp.PWM(self.pin, self.hertz)
        self.output.start(self.level)

    def __enter__(self):
        return self

    def shutdown(self):
        self.set_level(self.min_level)
        self.output.stop()

    def set_level(self, level):
        if self.min_level <= level <= self.max_level:
            self.level = level
            self.output.ChangeDutyCycle(level)

    def random(self):
        self.set_level(random.randint(self.min_level, self.max_level))

    def up(self):
        if self.level < self.max_level:
            self.set_level(self.level + 1)

    def down(self):
        if self.level > self.min_level:
            self.set_level(self.level - 1)

    def ramp_to(self, target_level, total_seconds):
        levels = abs(target_level - self.level)
        if levels > 0:
            step_duration = float(total_seconds) / float(levels)
        else:
            step_duration = 0.01
        # print(self.level, "to", target_level, " ", levels, "levels", step_duration)

        if target_level < self.level:
            while target_level < self.level:
                self.down()
                time.sleep(step_duration)
        elif target_level > self.level:
            while target_level > self.level:
                self.up()
                time.sleep(step_duration)


class LEDS:
    def __init__(self, gpio, red_pin, green_pin, blue_pin, white_pin):
        self.leds = {'red': LED(gpio, red_pin),
                     'green': LED(gpio, green_pin),
                     'blue': LED(gpio, blue_pin),
                     'white': LED(gpio, white_pin)}
        self.gp = gpio
        self.r = self.leds['red']
        self.g = self.leds['green']
        self.b = self.leds['blue']
        self.w = self.leds['white']

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        for l in self.leds:
            self.leds[l].shutdown()
        time.sleep(0.02)
        self.gp.cleanup()

    def __getitem__(self, item):
        if item in self.leds:
            return self.leds[item]
        else:
            return None

    def random(self):
        for l in self.leds:
            led = self.leds[l]
            to = random.randint(led.min_level, led.max_level)
            print(l, led.level, "to", to)
            led.ramp_to(to, 0.01)

    def startup(self):
        for l in ('red', 'green', 'blue', 'white'):
            led = self.leds[l]
            led.ramp_to(led.max_level, 0.5)
            time.sleep(1)
            led.ramp_to(led.min_level, 0.5)

    def blink_cycle(self, count):
        r = self.leds['red']
        g = self.leds['green']
        b = self.leds['blue']
        w = self.leds['white']

        r.set_level(r.min_level)
        b.set_level(g.min_level)
        g.set_level(b.min_level)
        w.set_level(w.min_level)

        for i in range(count):
            r.ramp_to(r.max_level, 1)
            time.sleep(1)
            r.ramp_to(r.min_level, 0.5)
            g.ramp_to(g.max_level, 1)
            time.sleep(1)
            g.ramp_to(g.min_level, 0.5)
            b.ramp_to(b.max_level, 1)
            time.sleep(1)
            b.ramp_to(b.min_level, 0.5)
            w.ramp_to(w.max_level, 1)
            time.sleep(1)
            w.ramp_to(w.min_level, 0.5)

    def dawn(self):
        r = self.leds['red']
        b = self.leds['blue']
        w = self.leds['white']
        r.ramp_to(r.max_level/2, 300)
        r.ramp_to(r.max_level, 300)
        w.ramp_to(w.max_level, 300)
        b.ramp_to(b.max_level, 60)
        time.sleep(60)
        r.ramp_to(r.min_level, 0.5)
        b.ramp_to(b.min_level, 0.5)
        time.sleep(180)
        self.blink_cycle(6)
        for i in range(r.max_level):
            for l in self.leds:
                self.leds[l].down()
            time.sleep(1)


if __name__ == '__main__':
    GPIO.setmode(GPIO.BOARD)
    # Configure GPIO pin numbers here
    with LEDS(GPIO, 40, 38, 37, 36) as leds:
        try:
            clock = Alarm(leds)
            clock_thread = threading.Thread(target=clock.run)
            clock_thread.daemon = True
            clock_thread.start()

            api = falcon.API()
            api.req_options.auto_parse_form_urlencoded = True
            api.add_route('/lights', Lights(leds))
            api.add_route('/lights/ramp', LightsRamp(leds))
            httpd = simple_server.make_server('', 8000, api)
            print("Web server thread starting")
            web_thread = threading.Thread(target=httpd.serve_forever)
            web_thread.daemon = True
            web_thread.start()

            while clock_thread.is_alive() and web_thread.is_alive():
                time.sleep(0.1)

        except (KeyboardInterrupt, SystemExit):
            print '\n! Shutting down\n'
            sys.exit(0)