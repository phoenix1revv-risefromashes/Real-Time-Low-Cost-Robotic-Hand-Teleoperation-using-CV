import json
from pathlib import Path

import pytest

from robotic_hand.config import load_config


def test_load_valid(cfg):
    assert list(cfg.fingers) == ["thumb", "index", "middle", "ring", "pinky"]
    assert cfg.required_stable_frames == 5


def test_rejects_unsafe_angle(tmp_path, cfg):
    config_file = Path(__file__).parents[1] / "config" / "hand_config.json"
    data = json.loads(config_file.read_text())
    data["fingers"]["thumb"]["servo_open_deg"] = 170
    p = tmp_path / "unsafe.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="servo endpoints"):
        load_config(p)


def test_rejects_extra_keys(tmp_path):
    config_file = Path(__file__).parents[1] / "config" / "hand_config.json"
    data = json.loads(config_file.read_text())
    data["disable_safety"] = True
    p = tmp_path / "unsafe.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="keys"):
        load_config(p)
