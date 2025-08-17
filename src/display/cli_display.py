import asyncio
import os
import platform
from typing import Callable, Optional

from src.display.base_display import BaseDisplay

# Handle pynput import according to different operating systems
try:
    if platform.system() == "Windows":
        from pynput import keyboard as pynput_keyboard
    elif os.environ.get("DISPLAY"):
        from pynput import keyboard as pynput_keyboard
    else:
        pynput_keyboard = None
except ImportError:
    pynput_keyboard = None


class CliDisplay(BaseDisplay):
    def __init__(self):
        super().__init__()
        self.running = True

        # Callback functions
        self.auto_callback = None
        self.abort_callback = None
        self.send_text_callback = None
        self.mode_callback = None

        # Asynchronous queue for processing commands
        self.command_queue = asyncio.Queue()

    async def set_callbacks(
        self,
        press_callback: Optional[Callable] = None,
        release_callback: Optional[Callable] = None,
        mode_callback: Optional[Callable] = None,
        auto_callback: Optional[Callable] = None,
        abort_callback: Optional[Callable] = None,
        send_text_callback: Optional[Callable] = None,
    ):
        """
        Set callback functions.
        """
        self.auto_callback = auto_callback
        self.abort_callback = abort_callback
        self.send_text_callback = send_text_callback
        self.mode_callback = mode_callback

    async def update_button_status(self, text: str):
        """
        Update button status.
        """
        print(f"Button status: {text}")

    async def update_status(self, status: str):
        """
        Update status text.
        """
        print(f"\rStatus: {status}        ", end="", flush=True)

    async def update_text(self, text: str):
        """
        Update TTS text.
        """
        if text and text.strip():
            print(f"\nText: {text}")

    async def update_emotion(self, emotion_name: str):
        """
        Update emotion display.
        """
        print(f"Emotion: {emotion_name}")

    async def start(self):
        """
        Start asynchronous CLI display.
        """
        print("\n=== Xiaozhi AI Command Line Control ===")
        print("Available commands:")
        print("  r     - Start/stop conversation")
        print("  x     - Interrupt current conversation")
        print("  q     - Exit program")
        print("  h     - Show this help message")
        print("  other - Send text message")
        print("============================\n")

        # Start command processing task
        command_task = asyncio.create_task(self._command_processor())
        input_task = asyncio.create_task(self._keyboard_input_loop())

        try:
            await asyncio.gather(command_task, input_task)
        except KeyboardInterrupt:
            await self.close()

    async def _command_processor(self):
        """
        Command processor.
        """
        while self.running:
            try:
                command = await asyncio.wait_for(self.command_queue.get(), timeout=1.0)
                if asyncio.iscoroutinefunction(command):
                    await command()
                else:
                    command()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Command processing error: {e}")

    async def _keyboard_input_loop(self):
        """
        Keyboard input loop.
        """
        try:
            while self.running:
                cmd = await asyncio.to_thread(input)
                await self._handle_command(cmd.lower().strip())
        except asyncio.CancelledError:
            pass

    async def _handle_command(self, cmd: str):
        """
        Handle command.
        """
        if cmd == "q":
            await self.close()
        elif cmd == "h":
            self._print_help()
        elif cmd == "r":
            if self.auto_callback:
                await self.command_queue.put(self.auto_callback)
        elif cmd == "x":
            if self.abort_callback:
                await self.command_queue.put(self.abort_callback)
        else:
            if self.send_text_callback:
                await self.send_text_callback(cmd)

    async def close(self):
        """
        Close CLI display.
        """
        self.running = False
        print("\nClosing application...")

    def _print_help(self):
        """
        Print help message.
        """
        print("\n=== Xiaozhi AI Command Line Control ===")
        print("Available commands:")
        print("  r     - Start/stop conversation")
        print("  x     - Interrupt current conversation")
        print("  q     - Exit program")
        print("  h     - Show this help message")
        print("  other - Send text message")
        print("============================\n")

    async def toggle_mode(self):
        """
        Mode switching in CLI mode (no operation)
        """
        self.logger.debug("Mode switching is not supported in CLI mode")

    async def toggle_window_visibility(self):
        """
        Window switching in CLI mode (no operation)
        """
        self.logger.debug("Window switching is not supported in CLI mode")
