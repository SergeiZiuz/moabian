# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import sys
import time
import requests
import numpy as np
import logging as log

from env import MoabEnv
from common import Vector2

class BrainNotFound(Exception):
    pass


# Controllers ------------------------------------------------------------------
def pid_controller(
    Kp=75,  # Proportional coefficient
    Ki=0.5,  # Integral coefficient
    Kd=45,  # Derivative coefficient
    max_angle=22,
    **kwargs,
):
    def next_action(state):
        env_state, ball_detected, buttons = state
        x, y, vel_x, vel_y, sum_x, sum_y = env_state

        if ball_detected:
            action_x = Kp * x + Ki * sum_x + Kd * vel_x
            action_y = Kp * y + Ki * sum_y + Kd * vel_y
            action_x = np.clip(action_x, -max_angle, max_angle)
            action_y = np.clip(action_y, -max_angle, max_angle)

            action = Vector2(action_x, action_y)

        else:
            # Move plate back to flat
            action = Vector2(0, 0)

        return action, {}

    return next_action


def joystick_controller(max_angle=16, **kwargs):
    def next_action(state):
        env_state, ball_detected, buttons = state
        action = Vector2(-buttons.joy_x, -buttons.joy_y)
        return action * max_angle, {}

    return next_action


def _brain_controller(
    max_angle=22,
    port=5555,
    alert_fn=lambda toggle: None,
    **kwargs,
):
    """
    This class interfaces with an HTTP server running locally.
    It passes the current hardware state and gets new plate
    angles in return.

    The hardware state is unprojected from camera pixel space
    back to real space by using the calculated plate surface plane.
    """
    prediction_url = f"http://localhost:{port}/v1/prediction"

    def next_action(state):
        env_state, ball_detected, buttons = state
        x, y, vel_x, vel_y, sum_x, sum_y = env_state

        observables = {
            "ball_x": x,
            "ball_y": y,
            "ball_vel_x": vel_x,
            "ball_vel_y": vel_y,
        }

        action = Vector2(0, 0)  # Action is 0,0 if not detected or brain didn't work
        info = {"status": 400, "resp": ""}
        if ball_detected:

            # Trap on GET failures so we can restart the brain without
            # bringing down this run loop. Plate will default to level
            # when it loses the connection.
            try:
                # Get action from brain
                response = requests.get(prediction_url, json=observables)
                info = {"status": response.status_code, "resp": response.json()}
                action_json = response.json()

                if response.ok:
                    if alert_fn is not None:
                        alert_fn(False)
                    action_json = requests.get(prediction_url, json=observables).json()
                    pitch = action_json["input_pitch"]
                    roll = action_json["input_roll"]

                    # Scale and clip
                    pitch = np.clip(pitch * max_angle, -max_angle, max_angle)
                    roll = np.clip(roll * max_angle, -max_angle, max_angle)

                    # To match how the old brain works (only integer plate angles)
                    pitch, roll = int(pitch), int(roll)

                    action = Vector2(-roll, pitch)
                else:
                    if alert_fn is not None:
                        alert_fn(True)

            except requests.exceptions.ConnectionError as e:
                print(f"No brain listening on port: {port}", file=sys.stderr)
                raise BrainNotFound

            except Exception as e:
                print(f"Brain exception: {e}")

        return action, info

    return next_action


def brain_controller_quick_switch(
    max_angle=22,
    port=5000,
    alert_fn=lambda toggle: None,
    **kwargs,
):
    """
    This class interfaces with an HTTP server running locally.
    It passes the current hardware state and gets new plate
    angles in return.

    The hardware state is unprojected from camera pixel space
    back to real space by using the calculated plate surface plane.


    This works the same as brain controller but will switch between a pair of two
    ports depending on which one is active/working.
    
    If port is a single number the spillover is port + 1.
    """
    if isinstance(port, tuple):
        port1, port2 = port
    elif isinstance(int(port), int):
        port1, port2 = int(port), int(port) + 1
    else:
        raise ValueError(f"{port} must be an int or a tuple of ints")

    port1_controller = _brain_controller(port=port1, **kwargs)
    port2_controller = _brain_controller(port=port2, **kwargs)
    pid_controller = pid_controller(**kwargs)

    prediction_url1 = f"http://localhost:{port1}/v1/prediction"
    prediction_url2 = f"http://localhost:{port2}/v1/prediction"

    def next_action(state):
        (x, y, vx, vy, _, _), ball_detected, buttons = state
        observables = {"ball_x": x, "ball_y": y, "ball_vel_x": vx, "ball_vel_y": vy}
        try:
            status_code1 = requests.get(prediction_url1, json=observables).status_code
        except:
            status_code1 = 400  # In case the port doesn't work at all
        try:
            status_code2 = requests.get(prediction_url2, json=observables).status_code
        except:
            status_code2 = 400  # In case the port doesn't work at all

        if status_code1 == 200:
            return port1_controller(state)
        elif status_code2 == 200:
            return port2_controller(state)
        else:
            # If neither port works fall back to PID controller
            return pid_controller(state)

    return next_action


# Export as the default brain controller
brain_controller = brain_controller_quick_switch
