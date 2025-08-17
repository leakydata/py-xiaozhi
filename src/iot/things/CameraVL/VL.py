import threading

from openai import OpenAI


class ImageAnalyzer:
    _instance = None
    _lock = threading.Lock()
    client = None

    def __init__(self):
        self.model = None

    def __new__(cls):
        """
        Ensure singleton pattern.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init(
        self,
        api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        models="qwen-omni-turbo",
    ):
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self.models = models

    @classmethod
    def get_instance(cls):
        """
        Get the camera manager instance (thread-safe)
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def analyze_image(
        self, base64_image, prompt="What scene is depicted in the image? Please describe it in detail, as the user may be blind."
    ) -> str:
        """
        Analyze the image and return the result.
        """
        completion = self.client.chat.completions.create(
            model=self.models,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant.",  # Use a string directly, not a list
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                },
            ],
            modalities=["text"],
            stream=True,
            stream_options={"include_usage": True},
        )
        mesag = ""
        for chunk in completion:
            if chunk.choices:
                mesag += chunk.choices[0].delta.content
            else:
                pass
        return mesag
