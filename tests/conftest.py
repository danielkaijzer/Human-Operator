"""
app.py imports cv2, utils.llm (anthropic), and utils.speech (RealtimeSTT,
pygame) at module level just to run the camera/voice loop in main(). None
of that is needed to test the pure functions (transform_actions_to_receiver_format,
repair_json_response, action_to_finger_mapping), and pygame.mixer.init() in
utils/speech.py will fail outright on a headless CI runner. Stub these three
in sys.modules before anything imports app, so tests only need flask, pyserial,
requests, and pytest installed.
"""
import sys
from unittest.mock import MagicMock

for _mod in ("cv2", "utils.llm", "utils.speech"):
    sys.modules.setdefault(_mod, MagicMock())
