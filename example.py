import multiprocessing as mp
import time

from pysimplegamepadsdl3 import (
    SDL_GAMEPAD_AXIS_LEFT_TRIGGER,
    SDL_GAMEPAD_AXIS_LEFTX,
    SDL_GAMEPAD_AXIS_LEFTY,
    SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
    SDL_GAMEPAD_AXIS_RIGHTX,
    SDL_GAMEPAD_AXIS_RIGHTY,
    SDL_GAMEPAD_BUTTON_DPAD_DOWN,
    SDL_GAMEPAD_BUTTON_DPAD_LEFT,
    SDL_GAMEPAD_BUTTON_DPAD_RIGHT,
    SDL_GAMEPAD_BUTTON_DPAD_UP,
    SDL_GAMEPAD_BUTTON_EAST,
    SDL_GAMEPAD_BUTTON_LEFT_SHOULDER,
    SDL_GAMEPAD_BUTTON_NORTH,
    SDL_GAMEPAD_BUTTON_RIGHT_SHOULDER,
    SDL_GAMEPAD_BUTTON_SOUTH,
    SDL_GAMEPAD_BUTTON_WEST,
    SDL_SENSOR_ACCEL,
    SDL_SENSOR_GYRO,
    Gamepad,
    GamepadState,
)

if __name__ == "__main__":
    with Gamepad(mp.Manager().dict()) as gamepad:  # type: ignore
        try:
            while not gamepad.gamepad_state_dict.keys():
                # Wait for a gamepad to be connected
                pass
            while True:
                state: GamepadState = gamepad.gamepad_state_dict[
                    # Take the gamepad with smallest id
                    gamepad.gamepad_state_dict.keys()[0]  # type: ignore
                ]
                print(
                    f"{state.axis[SDL_GAMEPAD_AXIS_LEFTX]=}, {state.axis[SDL_GAMEPAD_AXIS_LEFTY]=}, {state.axis[SDL_GAMEPAD_AXIS_RIGHTX]=}, {state.axis[SDL_GAMEPAD_AXIS_RIGHTY]=}, {state.axis[SDL_GAMEPAD_AXIS_LEFT_TRIGGER]=}, {state.axis[SDL_GAMEPAD_AXIS_RIGHT_TRIGGER]=}"
                )
                print(
                    f"{state.button[SDL_GAMEPAD_BUTTON_LEFT_SHOULDER]=}, {state.button[SDL_GAMEPAD_BUTTON_RIGHT_SHOULDER]=}"
                )
                print(
                    f"{state.button[SDL_GAMEPAD_BUTTON_SOUTH]=}, {state.button[SDL_GAMEPAD_BUTTON_EAST]=}, {state.button[SDL_GAMEPAD_BUTTON_WEST]=}, {state.button[SDL_GAMEPAD_BUTTON_NORTH]=}"
                )
                print(
                    f"{state.button[SDL_GAMEPAD_BUTTON_DPAD_UP]=}, {state.button[SDL_GAMEPAD_BUTTON_DPAD_DOWN]=}, {state.button[SDL_GAMEPAD_BUTTON_DPAD_LEFT]=}, {state.button[SDL_GAMEPAD_BUTTON_DPAD_RIGHT]=}"
                )
                print(
                    f"{state.sensor[SDL_SENSOR_ACCEL]=}, {state.sensor[SDL_SENSOR_GYRO]=}"
                )
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("Exiting...")
            gamepad.stop_event.set()
            gamepad.worker_process.join()
            print("Worker process terminated.")
