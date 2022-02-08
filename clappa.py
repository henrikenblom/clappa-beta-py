#!/usr/bin/env python3
import time

import numpy as np
import sounddevice as sd
from hue_api import HueApi
from hue_api.exceptions import UninitializedException, ButtonNotPressedException

first_clap_heard_at = 0.0
time_since_first_clap = 0.0
volume_limit = 40
individual_max_clap_duration = 0.08
hue = HueApi()
bridge_ip_address = "192.168.86.21"
office_lights = [33, 34, 37, 38, 39]


def audio_callback(in_data, _frames, audio_time, _status):
    volume_norm = int(np.linalg.norm(in_data) * 10)
    global first_clap_heard_at, time_since_first_clap
    if first_clap_heard_at > 0.0:
        time_since_first_clap = audio_time.currentTime - first_clap_heard_at
    if volume_norm > volume_limit:
        if time_since_first_clap > individual_max_clap_duration:
            toggle_lights()
            reset_globals()
        else:
            first_clap_heard_at = audio_time.currentTime
    if time_since_first_clap > 0.3:
        reset_globals()


def reset_globals():
    global first_clap_heard_at, time_since_first_clap
    first_clap_heard_at, time_since_first_clap = 0.0, 0.0


def connect_to_hue_bridge():
    try:
        hue.load_existing()
    except UninitializedException:
        connected = False
        print("Press the link button on the bridge")
        while not connected:
            try:
                hue.create_new_user(bridge_ip_address)
                hue.save_api_key()
                connected = True
            except ButtonNotPressedException:
                time.sleep(1)
    print("Connected to bridge")


def toggle_lights():
    print("Toggling lights")
    hue.toggle_on(office_lights)


def main():
    connect_to_hue_bridge()
    hue.fetch_lights()
    print("Controlling these lights:")
    for light in hue.filter_lights(office_lights):
        print(light)
    stream = sd.InputStream(callback=audio_callback)
    with stream:
        print("Running")
        while True:
            sd.sleep(100000)


if __name__ == "__main__":
    main()
