#!/usr/bin/env python
"""
MicroPython compatible module for making a strip of NeoPixels behave like an Alexa
"""
import math
import time
# Handle either desktop or micropython
try:
    import urandom
except ImportError:
    import random as urandom

# Globals - Most behaviors can be configured by changing these variables 
BLUE = (0, 5, 40)
CYAN = (0, 40, 40)
BLACK = (0, 0, 0)

# Number of lights in string - has to be even
NUM_LIGHTS = 20
# Number of lights wide for each segment when Alexa is "thinking"
ALEXA_ALTERNATING_FLASH_WIDTH = 2
# Must be even - width in LEDs of the cyan section that points at the user
ALEXA_POINTER_WIDTH = 4
ALEXA_HALF_POINTER_WIDTH = 2
ALEXA_LOOK_OFFSET_BASE = 2

# Frame rate of "playback" - has to be a float
FPS = 24.0
SLEEP_TIME = 1/FPS

# Setting for connections on an actual board
NEOPIXEL_PIN = None
BUTTON_PIN = None

def pprint(np):
    """
    Utility function approximating pprint.pprint for lists
    :param list np: A list of items to print out
    :returns: None
    """
    np = list(np)
    print('[' + str(np[0]) + ',')
    for i in range(len(np)):
        # Don't do anything for first and last items
        if i == 0 or i == (len(np)-1):
            continue
        print(' ' + str(np[i]) + ',')
    print(' ' + str(np[-1]) + ']')


def set_neopixel_to_list(np, input_list):
    """
    Utility function to loop over a list and set a neopixel object to it's contents
    :param neopixel.NeoPixel np: The neopixel object to assign the list to
    :param list input_list: Input list of typles to assign to the neopixels
    :returns: neopixel.NeoPixel 
    """
    for i in range(len(input_list)):
        np[i] = input_list[i]
    return np


class AlexaNeoPixelController:
    """
    Class for making a strip of neopixels behave like Alexa.
    """
    def __init__(self, np_pin=None, button_pin=None):
        """
        Initializes the Neopixel strip - or if no pin is provided will print output
        :param int np_pin: The pin number the neopixel strip is connected to
        :param int button_pin: The pin number of a button for triggering behaviors
        """
        self.np_pin = np_pin

        # This can either be run on an ESP8266 actually connected to a Neopixel strip
        # or on a desktop computer where it will just print output for easier debugging
        if self.np_pin is not None:
            import machine
            import neopixel
            self.np = neopixel.NeoPixel(machine.Pin(np_pin), NUM_LIGHTS)
        else:
            self.np = [()]*NUM_LIGHTS
        # If there is a button connected set it up to trigger self.play when pressed
        if button_pin is not None:
            import machine
            button = machine.Pin(button_pin, machine.Pin.IN)
            button.irq(trigger=machine.Pin.IRQ_FALLING, handler=self.play)
        pprint(self.np)
        # Set strip to all off
        self.np = set_neopixel_to_list(self.np, [BLACK] * NUM_LIGHTS)
        # Use self.np_pin to differentiate an actual neopixel.Neopixel from a list
        if self.np_pin:
            self.np.write()
        else:
            print('In __init__:')
            pprint(self.np)
        time.sleep(SLEEP_TIME)

    def turn_on(self):
        """
        Plays an animation approximating Alexa's turn on animation
        :returns: None
        """
        # Set the two opposite ends of the strip to each have 
        # half of Alexa's pointer's width CYAN
        print('1')
        for i in range(ALEXA_HALF_POINTER_WIDTH):
            self.np[i] = CYAN
            self.np[-1+(i*-1)] = CYAN
        print('2')
        # Do this until there are no more black pixels
        np_cache = list(self.np)
        while BLACK in np_cache:
            print('3')
            # Iterating over half the number of pixels because we will work inward
            # from both sides
            for index in range(NUM_LIGHTS/2):
                # Front end we are pushing the pointer segment to the middle
                if np_cache[index] == BLACK and np_cache[index-1] == CYAN:
                    print('settings %d CYAN' % index)
                    self.np[index] = CYAN
                    self.np[index - ALEXA_HALF_POINTER_WIDTH] = BLUE
                back_index = NUM_LIGHTS - index - 1
                # If back end we are pulling the pointer segment to the middle
                if np_cache[back_index] == BLACK and np_cache[back_index+1] == CYAN:
                    print('settings %d CYAN' % back_index)
                    self.np[back_index] = CYAN
                    self.np[back_index + ALEXA_HALF_POINTER_WIDTH] = BLUE
            print('4')
            if self.np_pin:
                print('4.5')
                self.np.write()
            else:
                print('Turning on:')
                pprint(self.np)
            print('5')
            np_cache = list(self.np)
            pprint(np_cache)
            time.sleep(SLEEP_TIME)
            print('6')
        # Pause extra long here not just one frame
        time.sleep(SLEEP_TIME*32)
        print('DONE')

    def look_around(self):
        """
        Plays an animation where the pointer will change position 1-2 times.
        Approximating when Alexa is indicating the audio source moving.
        :returns: None
        """
        # getrandbits(1) returns a number that is either 0 or 1
        num_times_to_look = urandom.getrandbits(1) + 1
        for i in range(num_times_to_look):
            current_center = list(self.np).index(CYAN) + ALEXA_HALF_POINTER_WIDTH
            offset = (urandom.getrandbits(1) + 1) * ALEXA_LOOK_OFFSET_BASE
            # Hover around true center
            if current_center > NUM_LIGHTS/2:
                offset *= -1
            new_center = current_center + offset
            # Don't want to deal with wrapping around properly or ensuring this
            # Doesn't produce a new_center that is too far to one side or the other
            # So lazily make sure that we don't go out of bounds
            new_center = min(new_center, NUM_LIGHTS-ALEXA_HALF_POINTER_WIDTH)
            new_center = max(new_center, ALEXA_HALF_POINTER_WIDTH)

            # Determining the indices of the pixels that will now be cyan
            new_cyan_pixels = range(new_center-2, new_center+2)

            for i in range(NUM_LIGHTS):
                self.np[i] = CYAN if i in new_cyan_pixels else BLUE

            if self.np_pin:
                self.np.write()
            else:
                print('Looking around:')
                pprint(self.np)
            # Pause extra long here not just one frame
            time.sleep(SLEEP_TIME*32)

    def alternating_flash(self):
        """
        Play an animation approximating Alexa's thinking animation.
        Short alternating segments of BLUE/CYAN rapidly alternate colors
        :returns: None
        """
        pass

    def alternating_pulse_fade(self):
        """
        Play an animation approximating Alexa's other "thinking" animation.
        After alternating flash flash to full CYAN then pulse between BLUE and CYAN
        :returns: None
        """
        for i in range(3):
            self.fade_to_color(CYAN, frames=SLEEP_TIME*12)
            self.fade_to_color(BLUE, frames=SLEEP_TIME*12)

        time.sleep(SLEEP_TIME*32)

    def turn_off(self):
        """
        Opposite of turn_on animation. The pointer breaks in half and retreats
        leaving BLACK behind it until the full strip is BLACK
        """
        self.fade_to_color(BLACK)

    def fade_to_color(self, color, frames=10):
        """
        Given an RGB Tuple fade entire string from it's current values to that color.
        Take given number of frames to complete transition
        :param tuple color: A tuple of ints from 0-255
        :param int frames: Number of frames to complete transition
        :returns: None
        """
        np_cache = list(self.np)
        # Take indicated number of frames
        for frame in range(frames):
            # Account for any rounding issues by just explicitly setting color at end
            if frame == frames-1:
                self.np = set_neopixel_to_list(self.np, [color] * NUM_LIGHTS)
            else:
                for pixel in range(len(np_cache)):
                    starting_color = np_cache[pixel]
                    # Determining new color by taking starting color and
                    # getting difference between that and target color then
                    # dividing that by the total number of frames and
                    # multiplying by the current frame
                    # Finally add that calculated offset to the starting color
                    red_offset = math.trunc((color[0] - starting_color[0])/frames)*(frame+1)
                    green_offset = math.trunc((color[1] - starting_color[1])/frames)*(frame+1)
                    blue_offset = math.trunc((color[2] - starting_color[2])/frames)*(frame+1)
                    new_color = (starting_color[0] + red_offset,
                                 starting_color[1] + green_offset,
                                 starting_color[2] + blue_offset)

                    self.np[pixel] = new_color
            if self.np_pin:
                self.np.write()
            else:
                print('Fading:')
                pprint(self.np)
            time.sleep(SLEEP_TIME)

    def play(self):
        """
        Standard play routine - Alexa turning on receiving a command and turning off
        :returns: None
        """
        self.turn_on()
        self.look_around()
        self.alternating_flash()
        self.alternating_pulse_fade()
        self.turn_off()


def unit_test():
    """
    Run through a bunch of possible light combinations as quickly as possible
    Mostly checking exceptions due to math issues
    :returns: None
    """
    global NUM_LIGHTS
    global ALEXA_POINTER_WIDTH
    global SLEEP_TIME

    NUM_LIGHTS = 4
    ALEXA_POINTER_WIDTH = 2
    SLEEP_TIME = 0

    for i in range(0, 512):
        print('NUM_LIGHTS ', str(NUM_LIGHTS))
        print('POINTER_WIDTH ', str(ALEXA_POINTER_WIDTH))
        npc = AlexaNeoPixelController()
        npc.play()
        time.sleep(1)
        del(npc)
        NUM_LIGHTS += 2
        if i%4:
            ALEXA_POINTER_WIDTH += 2

npc = AlexaNeoPixelController(np_pin=4, button_pin=0)
npc.play()

# if __name__ == "__main__":
#     npc = AlexaNeoPixelController()
#     npc.play()
    # unit_test()