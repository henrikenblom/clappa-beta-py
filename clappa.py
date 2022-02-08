#!/usr/bin/env python3
import argparse
import logging
import os
import re
import sys
import time

import discoverhue as discoverhue
import numpy as np
import pyfiglet as pyfiglet
import sounddevice as sd
from colorama import Fore, Style
from hue_api import HueApi
from hue_api.exceptions import UninitializedException, ButtonNotPressedException

first_clap_heard_at = 0.0
time_since_first_clap = 0.0
volume_limit = 40
individual_max_clap_duration = 0.08
total_max_clap_duration = 0.3
hue = HueApi()
selected_lights = []
settings_dir = ".clappa/"
hue_client_settings = settings_dir + "hue_client_settings"
lights_settings = settings_dir + "lights_settings.npy"

parser = argparse.ArgumentParser()
parser.add_argument('-log',
                    '--loglevel',
                    default='warning',
                    help='Set logging level.')
parser.add_argument('-cl',
                    action='store_true',
                    help='Run the light configuration wizard.')

args = parser.parse_args()

logging.basicConfig(level=args.loglevel.upper(),
                    format='%(asctime)s %(message)s')


def reset_globals():
    global first_clap_heard_at, time_since_first_clap
    first_clap_heard_at, time_since_first_clap = 0.0, 0.0


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
    if time_since_first_clap > total_max_clap_duration:
        reset_globals()


def toggle_lights():
    logging.info("Toggling lights")
    hue.fetch_lights()
    hue.toggle_on(selected_lights)


def connect_to_hue_bridge():
    try:
        hue.load_existing(hue_client_settings)
    except UninitializedException:
        connected = False
        bridge_ip_address = find_bridge()
        print("Connecting to bridge at", bridge_ip_address)
        print("Press the link button on the bridge")
        while not connected:
            try:
                hue.create_new_user(bridge_ip_address)
                os.mkdir(settings_dir)
                hue.save_api_key(hue_client_settings)
                connected = True
            except ButtonNotPressedException:
                time.sleep(1)
    print("Connected to bridge")


def find_bridge():
    print("Trying to find a Hue bridge")
    found_bridges = discoverhue.find_bridges()
    if len(found_bridges) == 0:
        sys.exit("No bridge found")
    if len(found_bridges) > 1:
        sys.exit("More than one bridge found")
    bridge_url = next(iter(found_bridges.values()))
    bridge_ip_address = next(
        iter(re.findall("\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3}", bridge_url)))
    return bridge_ip_address


def configure_lights():
    hue.fetch_lights()
    if args.cl:
        set_selected_lights_by_user_input()
    else:
        try:
            set_selected_lights_from_file()
        except FileNotFoundError:
            set_selected_lights_by_user_input()


def set_selected_lights_from_file():
    global selected_lights
    selected_lights = np.load(lights_settings).tolist()


def set_selected_lights_by_user_input():
    global selected_lights
    selected_lights = get_user_light_selection()
    np.save(lights_settings, selected_lights)


def get_user_light_selection():
    print("Available lights:")
    valid_indices = []
    for light in hue.fetch_lights():
        valid_indices.append(light.id)
        print(light)
    selected_lights_string = input(
        "Enter the corresponding numbers of the lights you wish to control "
        "(separated by commas): ")
    try:
        parsed_list = list(map(int, selected_lights_string.split(",")))
        if set(parsed_list).issubset(valid_indices):
            return parsed_list
        else:
            print("Please only select lights included in the list")
            return get_user_light_selection()
    except ValueError:
        print("Invalid input:", selected_lights_string)
        return get_user_light_selection()


def print_logo():
    figlet = pyfiglet.Figlet(font='vortron_')
    print()
    print(Fore.CYAN + figlet.renderText("CLAPPA BETA PY"))
    print(Style.RESET_ALL)


def main():
    print_logo()
    connect_to_hue_bridge()
    configure_lights()
    logging.debug("Controlling these lights:")
    for light in hue.filter_lights(selected_lights):
        logging.debug(light)
    stream = sd.InputStream(callback=audio_callback)
    with stream:
        print("Running - double clap to toggle lights! 👏👏->💡")
        while True:
            sd.sleep(100000)


if __name__ == "__main__":
    main()
