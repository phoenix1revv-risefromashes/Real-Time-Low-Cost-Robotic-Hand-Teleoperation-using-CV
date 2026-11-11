from pathlib import Path

import pytest

from robotic_hand.config import HandConfig, load_config


@pytest.fixture
def cfg() -> HandConfig:
    return load_config(Path(__file__).parents[1] / "config" / "hand_config.json")
