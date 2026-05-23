import copy
import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from app.services.comfy_client import ComfyClient, build_room_render_workflow

WORKFLOW_TEMPLATE = {
    "client_id": "house-diy-test",
    "prompt": {
        "5": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["3", 0], "text": "{{prompt}}"}},
        "8": {"class_type": "KSampler", "inputs": {"seed": 42}},
        "10": {"class_type": "SaveImage", "inputs": {"filename_prefix": "house-diy/test"}},
    },
}


@pytest.fixture
def workflow_path(tmp_path: Path, monkeypatch):
    path = tmp_path / "room_render_api.json"
    path.write_text(json.dumps(WORKFLOW_TEMPLATE), encoding="utf-8")
    monkeypatch.setattr(
        "app.services.comfy_client.DEFAULT_WORKFLOW_PATH",
        path,
    )
    return path


def test_build_room_render_workflow(workflow_path):
    workflow = build_room_render_workflow(
        prompt="modern bedroom",
        seed=99,
        filename_prefix="house-diy/r1",
    )
    assert workflow["prompt"]["5"]["inputs"]["text"] == "modern bedroom"
    assert workflow["prompt"]["8"]["inputs"]["seed"] == 99
    assert workflow["prompt"]["10"]["inputs"]["filename_prefix"] == "house-diy/r1"


def test_submit_prompt_returns_prompt_id(workflow_path):
    client = ComfyClient(base_url="http://127.0.0.1:8188")
    mock_response = MagicMock()
    mock_response.json.return_value = {"prompt_id": "abc-123"}
    mock_response.raise_for_status = MagicMock()

    workflow = build_room_render_workflow("test prompt", 1, "house-diy/x")
    with pytest.MonkeyPatch.context() as mp:
        mock_http = MagicMock()
        mock_http.post.return_value = mock_response
        mp.setattr(client, "_client", mock_http)
        prompt_id = client.submit_prompt(workflow)
    assert prompt_id == "abc-123"
    mock_http.post.assert_called_once()
