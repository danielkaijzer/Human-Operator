#!/usr/bin/env python3
"""
Minimal Claude API client with vision support.
"""

import anthropic
import base64
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    def __init__(self, model: str = "claude-opus-4-5", max_tokens: int = 512):
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        self.model = model
        self.max_tokens = max_tokens

    def ask_with_image(self, prompt: str, image_bytes: bytes, media_type: str = "image/jpeg") -> str:
        """Send a prompt + image to Claude and return the text response."""
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_b64,
                            },
                        }, # type: ignore
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )
        
        return message.content[0].text # type: ignore

if __name__ == "__main__":
    import cv2
    import numpy as np
    import time
    
    # Example usage
    client = LLMClient()

    #latency test with a simple image prompt

    # create a simple red square image for testing
    red_square = np.zeros((100, 100, 3), dtype=np.uint8)
    red_square[:] = (255, 0, 0)  # Red in BGR format
    _, image_bytes = cv2.imencode(".jpg", red_square)

    # timing the response
    start_time = time.time()
    response = client.ask_with_image("What do you see in this image?", image_bytes.tobytes())
    end_time = time.time()
    print(f"Response time: {end_time - start_time:.2f} seconds")
    print("Claude's response:", response)
