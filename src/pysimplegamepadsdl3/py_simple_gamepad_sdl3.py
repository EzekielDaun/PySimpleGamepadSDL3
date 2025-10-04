import multiprocessing as mp
from collections import defaultdict
from ctypes import c_float
from dataclasses import dataclass, field
from multiprocessing.managers import DictProxy
from multiprocessing.synchronize import Event

from sdl3 import (
    SDL_EVENT_GAMEPAD_ADDED,
    SDL_EVENT_GAMEPAD_AXIS_MOTION,
    SDL_EVENT_GAMEPAD_BUTTON_DOWN,
    SDL_EVENT_GAMEPAD_BUTTON_UP,
    SDL_EVENT_GAMEPAD_REMOVED,
    SDL_EVENT_GAMEPAD_SENSOR_UPDATE,
    SDL_EVENT_GAMEPAD_TOUCHPAD_DOWN,
    SDL_EVENT_GAMEPAD_TOUCHPAD_MOTION,
    SDL_EVENT_GAMEPAD_TOUCHPAD_UP,
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
    SDL_INIT_GAMEPAD,
    SDL_INIT_VIDEO,
    SDL_SENSOR_ACCEL,
    SDL_SENSOR_GYRO,
    SDL_CloseGamepad,
    SDL_Event,
    SDL_GamepadHasSensor,
    SDL_GetError,
    SDL_GetGamepadAxis,
    SDL_GetGamepadButton,
    SDL_GetGamepadFromID,
    SDL_GetGamepadSensorData,
    SDL_Init,
    SDL_JoystickID,
    SDL_OpenGamepad,
    SDL_Quit,
    SDL_SetGamepadSensorEnabled,
    SDL_WaitEventTimeout,
)
from sdl3.SDL_events import (
    SDL_GamepadAxisEvent,
    SDL_GamepadButtonEvent,
    SDL_GamepadDeviceEvent,
    SDL_GamepadSensorEvent,
    SDL_GamepadTouchpadEvent,
)


def _default_tuple_float3():
    return (0.0, 0.0, 0.0)


@dataclass(frozen=True)
class GamepadState:
    axis: defaultdict[int, int] = field(default_factory=lambda: defaultdict(int))
    button: defaultdict[int, bool] = field(default_factory=lambda: defaultdict(bool))
    sensor: defaultdict[int, tuple[float, float, float]] = field(
        default_factory=lambda: defaultdict(_default_tuple_float3)
    )


@dataclass(frozen=True)
class Gamepad:
    gamepad_state_dict: DictProxy  # DictProxy[SDL_JoystickID, GamepadState]
    sdl_wait_event_timeout_ms: int = int(1e3 / 120)  # Default 120 Hz
    stop_event: Event = field(default_factory=mp.Event)
    worker_process: mp.Process = field(init=False)

    def __post_init__(self):
        assert isinstance(
            self.gamepad_state_dict, DictProxy
        ), "gamepad_state_dict must be a multiprocessing.managers.DictProxy"

        object.__setattr__(
            self,
            "worker_process",
            mp.Process(
                target=self._worker,
                args=(
                    self.stop_event,
                    self.gamepad_state_dict,
                    self.sdl_wait_event_timeout_ms,
                ),
            ),
        )

    def __enter__(self):
        self.worker_process.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop_event.set()
        self.worker_process.join()

    @staticmethod
    def _worker(
        stop_event: Event, state_dict: dict[SDL_JoystickID, GamepadState], timeout: int
    ):
        if not SDL_Init(SDL_INIT_GAMEPAD | SDL_INIT_VIDEO):  # type: ignore
            raise RuntimeError(f"SDL_Init failed: {SDL_GetError()}")
        while not stop_event.is_set():
            e = SDL_Event()
            if SDL_WaitEventTimeout(e, timeout):  # type: ignore
                if e.type == SDL_EVENT_GAMEPAD_ADDED:  # type: ignore
                    gamepad_device_event: SDL_GamepadDeviceEvent = e.gdevice  # type: ignore
                    gamepad = SDL_OpenGamepad(gamepad_device_event.which)
                    if gamepad:
                        # Enable sensors if available
                        for sensor_type in [SDL_SENSOR_ACCEL, SDL_SENSOR_GYRO]:
                            if SDL_GamepadHasSensor(gamepad, sensor_type):  # type: ignore
                                SDL_SetGamepadSensorEnabled(gamepad, sensor_type, True)  # type: ignore
                        # Initialize state
                        gamepad_dict = state_dict
                        gamepad_dict[gamepad_device_event.which] = GamepadState()
                        state_dict = gamepad_dict
                elif e.type == SDL_EVENT_GAMEPAD_REMOVED:  # type: ignore
                    gamepad_device_event: SDL_GamepadDeviceEvent = e.gdevice  # type: ignore
                    if gamepad_device_event.which in state_dict:
                        del state_dict[gamepad_device_event.which]
                        SDL_CloseGamepad(gamepad_device_event.which)
                elif e.type == SDL_EVENT_GAMEPAD_AXIS_MOTION:  # type: ignore
                    axis_event: SDL_GamepadAxisEvent = e.gaxis  # type: ignore
                    if axis_event.which in state_dict:
                        gamepad_dict = state_dict[axis_event.which]
                        gamepad_dict.axis.update({axis_event.axis: axis_event.value})
                        state_dict[axis_event.which] = gamepad_dict
                elif e.type in [SDL_EVENT_GAMEPAD_BUTTON_DOWN, SDL_EVENT_GAMEPAD_BUTTON_UP]:  # type: ignore
                    button_event: SDL_GamepadButtonEvent = e.gbutton  # type: ignore
                    if button_event.which in state_dict:
                        gamepad_dict = state_dict[button_event.which]
                        gamepad_dict.button[button_event.button] = button_event.down
                        state_dict[button_event.which] = gamepad_dict
                elif e.type == SDL_EVENT_GAMEPAD_SENSOR_UPDATE:  # type: ignore
                    sensor_event: SDL_GamepadSensorEvent = e.gsensor  # type: ignore
                    if sensor_event.which in state_dict:
                        gamepad_dict = state_dict[sensor_event.which]
                        gamepad_dict.sensor[sensor_event.sensor] = tuple(
                            sensor_event.data
                        )
                        state_dict[sensor_event.which] = gamepad_dict
                elif e.type in [SDL_EVENT_GAMEPAD_TOUCHPAD_DOWN, SDL_EVENT_GAMEPAD_TOUCHPAD_MOTION, SDL_EVENT_GAMEPAD_TOUCHPAD_UP]:  # type: ignore
                    touchpad_event: SDL_GamepadTouchpadEvent = e.gtouchpad  # type: ignore
                    if touchpad_event.which in state_dict:
                        # Handle touchpad events if needed, I don't have a gamepad with touchpad to test
                        pass
            else:  # Timeout, poll
                for gamepad_id, gamepad_dict in state_dict.items():
                    if gamepad := SDL_GetGamepadFromID(gamepad_id):
                        for k in [
                            SDL_GAMEPAD_AXIS_LEFTX,
                            SDL_GAMEPAD_AXIS_LEFTY,
                            SDL_GAMEPAD_AXIS_RIGHTX,
                            SDL_GAMEPAD_AXIS_RIGHTY,
                            SDL_GAMEPAD_AXIS_LEFT_TRIGGER,
                            SDL_GAMEPAD_AXIS_RIGHT_TRIGGER,
                        ]:
                            gamepad_dict.axis[k] = SDL_GetGamepadAxis(gamepad, k)  # type: ignore
                            state_dict[gamepad_id] = gamepad_dict
                        for k in [
                            SDL_GAMEPAD_BUTTON_LEFT_SHOULDER,
                            SDL_GAMEPAD_BUTTON_RIGHT_SHOULDER,
                            SDL_GAMEPAD_BUTTON_SOUTH,
                            SDL_GAMEPAD_BUTTON_EAST,
                            SDL_GAMEPAD_BUTTON_WEST,
                            SDL_GAMEPAD_BUTTON_NORTH,
                            SDL_GAMEPAD_BUTTON_DPAD_UP,
                            SDL_GAMEPAD_BUTTON_DPAD_DOWN,
                            SDL_GAMEPAD_BUTTON_DPAD_LEFT,
                            SDL_GAMEPAD_BUTTON_DPAD_RIGHT,
                        ]:
                            gamepad_dict.button[k] = SDL_GetGamepadButton(gamepad, k)  # type: ignore
                            state_dict[gamepad_id] = gamepad_dict
                        for k in [
                            SDL_SENSOR_ACCEL,
                            SDL_SENSOR_GYRO,
                        ]:
                            ctypes_sensor_data = (c_float * 3)()
                            if SDL_GetGamepadSensorData(
                                gamepad, k, ctypes_sensor_data, 3  # type: ignore
                            ):
                                gamepad_dict.sensor[k] = tuple(ctypes_sensor_data)
                            state_dict[gamepad_id] = gamepad_dict

        # Stop event, cleanup
        for gamepad_id in list(state_dict.keys()):
            if gamepad := SDL_GetGamepadFromID(gamepad_id):
                SDL_CloseGamepad(gamepad)
        SDL_Quit()
