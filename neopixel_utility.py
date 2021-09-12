import logging
from colour import Color
import random
import math
import collections
from neopixel import PrinterNeoPixel


GAMMA_TABLE_STEPS=100
Pattern = collections.namedtuple('Pattern','name function')

class NeopixelUtility(PrinterNeoPixel):
    def __init__(self, config):
        PrinterNeoPixel.__init__(self, config)
        name = config.get_name().split()[1]
        self.gcode = self.printer.lookup_object('gcode')
        self.reactor = self.printer.get_reactor()

        self.gamma = config.get('gamma', 2.7)
        self.gamma_adjust = config.getboolean('gamma_adjust', True)
        self.gamma_table = self._gamma_table(GAMMA_TABLE_STEPS, self.gamma)

        self.gcode.register_mux_command(
            "SET_LED_PATTERN", "LED", name,
            self.cmd_SET_LED_PATTERN,
            desc=self.cmd_SET_LED_PATTERN_help)

        self.gcode.register_mux_command(
            "SET_LED_ANIMATION", "LED", name,
            self.cmd_SET_LED_ANIMATION,
            desc=self.cmd_SET_LED_ANIMATION_help)

    # Parameters:
    # - SPEED Relative speed of animations to base ([0 to 10] -> default 1.)
    # - TERMINATE Length of time to run before terminating (for looping animations)
    # - RANGE Allow a subset of pixels to be set?


    # Animations (+ Animation Specific Parameters) / Separate into animations and allocations?  What about Rider?
    # Random
    # Rainbow
    # March  Direction, Speed, Steps
    # Pattern Pattern
    # Fade
    # Pulse
    # Solid Colour
    # Rider Pattern

    cmd_SET_LED_PATTERN_help = "Set a static pattern for the LEDs"
    def cmd_SET_LED_PATTERN(self, params):
        #logging.debug(self.get_status(None)['color_data'])
        pattern = params.get('PATTERN', 'Unknown')
        limits = map(int,params.get('RANGE', '1,{0}'.format(self.chain_count)).split(','))

        patterns = [
            Pattern('Random', self.__pattern_random),
            Pattern('Gradient', self.__pattern_gradient),
            Pattern('Custom', self.__pattern_custom)
        ]

        pattern_list = list(zip(*patterns))[0]

        if pattern not in pattern_list:
            pattern = 'Random'
            self.gcode.respond_info(
                'Using Random pattern.  Please select a pattern using' \
                ' PATTERN= and pass one of the following'\
                ' patterns: {}'.format(', '.join(pattern_list)))

        func = [x.function for x in patterns if x.name == pattern][0]
        logging.debug(pattern)
        logging.debug(func)
        func(params, limits)

    cmd_SET_LED_ANIMATION_help = "Start an animation"
    def cmd_SET_LED_ANIMATION(self, params):
        pass

    def __pattern_gradient(self, params, limits):
        ascending = params.get_int('ASCENDING', 1)

        if ascending:
            for i in range(1,self.chain_count):
                linear_gradient = float(i) / self.chain_count
                c = Color(rgb=(linear_gradient,linear_gradient,linear_gradient))
                if self.gamma_adjust:
                    self._set_neopixels(*self._gamma_convert(c).rgb,index=i, transmit=False)
                else:
                    self._set_neopixels(*c.grb, index=i, transmit=False)
            self._set_neopixels(1.,1.,1.,index=self.chain_count)
        else:
            for i in range(self.chain_count,1,-1):
                linear_gradient = float(self.chain_count - i + 1) / self.chain_count
                c = Color(rgb=(linear_gradient,linear_gradient,linear_gradient))
                if self.gamma_adjust:
                    self._set_neopixels(*self._gamma_convert(c).rgb,index=i, transmit=False)
                else:
                    self._set_neopixels(*c.grb, index=i, transmit=False)
            self._set_neopixels(1.,1.,1.,index=1)

    def __pattern_random(self, params, limits):
        for i in range(limits[0],limits[1]):
            self._set_neopixels(random.random(),random.random(),random.random(),index=i, transmit=False)
        self._set_neopixels(1.,1.,1.,index=limits[1])

    def __pattern_custom(self, params, limits):
        pass

    def _gamma_lookup(self, number):
        return self.gamma_table[int(round((GAMMA_TABLE_STEPS-1) * number))]

    def _gamma_convert(self, colour):
        return Color(rgb=map(self._gamma_lookup, colour.rgb))

    def _gamma_table(self, nsteps, gamma):
        gammaedUp = [math.pow(x, gamma) for x in range(nsteps)]
        return [x/max(gammaedUp) for x in gammaedUp]

    def _pause(self, time=0.):
        eventtime = self.reactor.monotonic()
        end  = eventtime + time
        while eventtime < end:
            eventtime = self.reactor.pause(eventtime + .05)

    # Copied relevant parts from neopixels SET_LED cmd
    def _set_neopixels(self, red, green, blue, white=1., index=None, transmit=True):
        def reactor_bgfunc(print_time):
            with self.mutex:
                #logging.info("Setting: {0} {1} {2}".format(red, green, blue))
                self.update_color_data(red, green, blue, white, index)
                if transmit:
                    self.send_data(print_time)
        def lookahead_bgfunc(print_time):
            self.reactor.register_callback(lambda et: reactor_bgfunc(print_time))

        # No sync - just do it
        lookahead_bgfunc(None)

def load_config_prefix(config):
    return NeopixelUtility(config)
