import asyncio
import json
from typing import Any, Dict, Optional, Tuple

from src.iot.thing import Thing
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ThingManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ThingManager()
        return cls._instance

    def __init__(self):
        self.things = []
        self.last_states = {}  # Add a state cache dictionary to store the last state

    async def initialize_iot_devices(self, config):
        """Initialize IoT devices.

        Note: The countdown timer function has been migrated to MCP tools to provide better AI integration and status feedback.
        """
        # from src.iot.things.CameraVL.Camera import Camera
        # from src.iot.things.countdown_timer import CountdownTimer  # Migrated to MCP
        # from src.iot.things.lamp import Lamp

        # from src.iot.things.music_player import MusicPlayer
        # from src.iot.things.speaker import Speaker
        # Add devices
        # self.add_thing(CountdownTimer())  # Migrated to MCP tools
        # self.add_thing(Lamp())
        # self.add_thing(Speaker())
        # self.add_thing(MusicPlayer())
        # self.add_thing(Camera())

    def add_thing(self, thing: Thing) -> None:
        self.things.append(thing)

    async def get_descriptors_json(self) -> str:
        """
        Get the descriptor JSON for all devices.
        """
        # Since get_descriptor_json() is a synchronous method (returns static data),
        # a simple synchronous call is sufficient here.
        descriptors = [thing.get_descriptor_json() for thing in self.things]
        return json.dumps(descriptors)

    async def get_states_json(self, delta=False) -> Tuple[bool, str]:
        """Get the state JSON for all devices.

        Args:
            delta: Whether to return only the changed parts. True means only return the changed parts.

        Returns:
            Tuple[bool, str]: A boolean indicating if there was a state change and the JSON string.
        """
        if not delta:
            self.last_states.clear()

        changed = False

        tasks = [thing.get_state_json() for thing in self.things]
        states_results = await asyncio.gather(*tasks)

        states = []
        for i, thing in enumerate(self.things):
            state_json = states_results[i]

            if delta:
                # Check if the state has changed
                is_same = (
                    thing.name in self.last_states
                    and self.last_states[thing.name] == state_json
                )
                if is_same:
                    continue
                changed = True
                self.last_states[thing.name] = state_json

            # Check if state_json is already a dictionary object
            if isinstance(state_json, dict):
                states.append(state_json)
            else:
                states.append(json.loads(state_json))  # Convert JSON string to dictionary

        return changed, json.dumps(states)

    async def get_states_json_str(self) -> str:
        """
        For compatibility with old code, keep the original method name and return value type.
        """
        _, json_str = await self.get_states_json(delta=False)
        return json_str

    async def invoke(self, command: Dict) -> Optional[Any]:
        """Invoke a device method.

        Args:
            command: A command dictionary containing name, method, etc.

        Returns:
            Optional[Any]: Returns the result of the call if the device is found and the call is successful; otherwise, raises an exception.
        """
        thing_name = command.get("name")
        for thing in self.things:
            if thing.name == thing_name:
                return await thing.invoke(command)

        # Log an error
        logger.error(f"Device not found: {thing_name}")
        raise ValueError(f"Device not found: {thing_name}")
