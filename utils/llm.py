#!/usr/bin/env python3
"""
Minimal vision-capable LLM client.

Supports two backends, selected at runtime so you can test cheaply without
touching call sites:
  - "anthropic"  (default): calls the Claude API directly via the anthropic SDK.
  - "openrouter": calls OpenRouter's OpenAI-compatible API via the openai SDK.

Pick the backend with the LLM_PROVIDER env var (or the `provider` arg).
"""

import os
import base64
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    def __init__(self, model: str | None = None, max_tokens: int = 512, provider: str | None = None):
        # Default to Anthropic; set LLM_PROVIDER=openrouter to test via OpenRouter.
        self.provider = (provider or os.getenv("LLM_PROVIDER", "anthropic")).lower()
        self.max_tokens = max_tokens

        if self.provider == "openrouter":
            from openai import OpenAI

            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv("OPENROUTER_API_KEY"),  # reads OPENROUTER_API_KEY from env
            )
            # OpenRouter model slugs are namespaced, e.g. "anthropic/claude-opus-4.1".
            self.model = model or os.getenv("OPENROUTER_MODEL", "anthropic/claude-opus-4.1")
        else:
            import anthropic

            self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
            self.model = model or "claude-opus-4-8"

    def ask_with_image(self, prompt: str, image_bytes: bytes, media_type: str = "image/jpeg") -> str:
        """Send a prompt + image to the configured LLM and return the text response."""
        image_b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

        if self.provider == "openrouter":
            # OpenAI-compatible vision format: image is a data: URL.
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{media_type};base64,{image_b64}"},
                            },
                        ],
                    }
                ],
            )
            return response.choices[0].message.content  # type: ignore

        # Anthropic Messages format: image is a base64 source block.
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
                        },  # type: ignore
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        )

        return message.content[0].text  # type: ignore


if __name__ == "__main__":
    import cv2
    import numpy as np
    import time

    # Example usage
    client = LLMClient()
    print(f"Provider: {client.provider} | Model: {client.model}")

    # latency test with a simple image prompt

    # create a simple red square image for testing
    red_square = np.zeros((100, 100, 3), dtype=np.uint8)
    red_square[:] = (0, 0, 255)  # Red in BGR
    _, image_bytes = cv2.imencode(".jpg", red_square)

    # timing the response
    start_time = time.time()
    response = client.ask_with_image("What do you see in this image?", image_bytes.tobytes())
    end_time = time.time()
    print(f"Response time: {end_time - start_time:.2f} seconds")
    print("Response:", response)
