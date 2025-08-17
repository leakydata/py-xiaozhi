import asyncio

from src.iot.thing import Parameter, Thing, ValueType
from src.utils.volume_controller import VolumeController


class Speaker(Thing):
    def __init__(self):
        super().__init__("Speaker", "The speaker of the current AI robot")

        # Initialize volume controller
        self.volume_controller = None
        try:
            if VolumeController.check_dependencies():
                self.volume_controller = VolumeController()
                self.volume = self.volume_controller.get_volume()
            else:
                self.volume = 70  # Default volume
        except Exception:
            self.volume = 70  # Default volume

        # Define properties
        self.add_property("volume", "Current volume level", self.get_volume)

        # Define methods
        self.add_method(
            "SetVolume",
            "Set Volume",
            [Parameter("volume", "An integer between 0 and 100", ValueType.NUMBER, True)],
            self._set_volume,
        )

    async def get_volume(self):
        # Try to get real-time volume from the volume controller
        if self.volume_controller:
            try:
                self.volume = self.volume_controller.get_volume()
            except Exception:
                pass
        return self.volume

    async def _set_volume(self, params):
        volume = params["volume"].get_value()
        if 0 <= volume <= 100:
            self.volume = volume
            try:
                # Directly use VolumeController to set system volume
                if self.volume_controller:
                    await asyncio.to_thread(self.volume_controller.set_volume, volume)
                else:
                    raise Exception("Volume controller not initialized")

                return {"success": True, "message": f"Volume has been set to: {volume}"}
            except Exception as e:
                print(f"Failed to set volume: {e}")
                return {"success": False, "message": f"Failed to set volume: {e}"}
        else:
            raise ValueError("Volume must be between 0 and 100")
