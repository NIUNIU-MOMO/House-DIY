import copy
import json
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_WORKFLOW_PATH = REPO_ROOT / "workflows" / "room_render_api.json"
DEPTH_WORKFLOW_PATH = REPO_ROOT / "workflows" / "room_render_depth_api.json"

WORKFLOW_T2I = "flux_interior_t2i_api"
WORKFLOW_DEPTH = "flux_interior_depth_api"


class ComfyClient:
    """ComfyUI HTTP 客户端"""

    def __init__(self, base_url: str | None = None, timeout: float = 300.0) -> None:
        self.base_url = (base_url or settings.house_diy_comfyui_base_url).rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def submit_prompt(self, workflow: dict[str, Any]) -> str:
        """
        提交 ComfyUI workflow

        @param workflow API 格式 workflow
        @return prompt_id
        """
        payload = copy.deepcopy(workflow)
        payload.setdefault("client_id", f"house-diy-{uuid.uuid4().hex[:8]}")
        response = self._client.post("/prompt", json=payload)
        response.raise_for_status()
        return response.json()["prompt_id"]

    def upload_image(self, image_bytes: bytes, filename: str) -> str:
        """
        上传控制图到 ComfyUI input 目录

        @param image_bytes PNG/JPEG 二进制
        @param filename 目标文件名
        @return ComfyUI 返回的文件名
        """
        response = self._client.post(
            "/upload/image",
            files={"image": (filename, image_bytes, "image/png")},
            data={"type": "input", "overwrite": "true"},
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("name") or filename

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        response = self._client.get(f"/history/{prompt_id}")
        response.raise_for_status()
        return response.json()

    def _history_entry(self, prompt_id: str) -> dict[str, Any] | None:
        history = self.get_history(prompt_id)
        return history.get(prompt_id)

    def _is_history_done(self, entry: dict[str, Any]) -> bool:
        status = entry.get("status", {})
        return bool(status.get("completed")) and bool(entry.get("outputs"))

    def wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: float = 2.0,
        timeout: float = 600.0,
        on_poll: Callable[[float, float], None] | None = None,
    ) -> dict[str, Any]:
        """
        轮询等待 ComfyUI 任务完成

        @param prompt_id 任务 ID
        @param poll_interval 轮询间隔秒
        @param timeout 超时秒
        @param on_poll 轮询进度回调 (elapsed_sec, timeout_sec)
        @return history 条目
        """
        started = time.time()
        deadline = started + timeout
        while time.time() < deadline:
            entry = self._history_entry(prompt_id)
            if entry is not None:
                status = entry.get("status", {})
                if status.get("status_str") == "error":
                    messages = status.get("messages") or []
                    raise RuntimeError(f"ComfyUI prompt {prompt_id} failed: {messages[-1] if messages else status}")
                if self._is_history_done(entry):
                    return entry
            if on_poll is not None:
                on_poll(time.time() - started, timeout)
            time.sleep(poll_interval)

        entry = self._history_entry(prompt_id)
        if entry is not None and self._is_history_done(entry):
            return entry
        raise TimeoutError(
            f"ComfyUI prompt {prompt_id} timed out after {int(timeout)}s "
            f"(FLUX 1024 单张通常需 5–10 分钟，可调大 HOUSE_DIY_COMFYUI_RENDER_TIMEOUT)"
        )

    def download_image(self, filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
        """
        下载 ComfyUI 输出图片

        @param filename 文件名
        @param subfolder 子目录
        @param folder_type 文件夹类型
        @return 图片二进制
        """
        response = self._client.get(
            "/view",
            params={"filename": filename, "subfolder": subfolder, "type": folder_type},
        )
        response.raise_for_status()
        return response.content


def load_workflow_template(path: Path | None = None) -> dict[str, Any]:
    template_path = path or DEFAULT_WORKFLOW_PATH
    return json.loads(template_path.read_text(encoding="utf-8"))


def resolve_render_workflow_name(controlnet: str | None) -> str:
    """
    根据 controlnet 配置选择 workflow 名称

    @param controlnet controlnet 类型
    @return workflow 标识
    """
    if controlnet == "layout_depth":
        return WORKFLOW_DEPTH
    return WORKFLOW_T2I


def _workflow_template_path(workflow_name: str) -> Path:
    if workflow_name == WORKFLOW_DEPTH:
        return DEPTH_WORKFLOW_PATH
    return DEFAULT_WORKFLOW_PATH


def build_room_render_workflow(
    prompt: str,
    seed: int,
    filename_prefix: str,
    template_path: Path | None = None,
    workflow_name: str = WORKFLOW_T2I,
    controlnet_image_name: str | None = None,
    controlnet_strength: float | None = None,
) -> dict[str, Any]:
    """
    构建参数化房间渲染 workflow

    @param prompt 正向提示词
    @param seed 随机种子
    @param filename_prefix 输出前缀
    @param template_path 模板路径
    @param workflow_name workflow 标识
    @param controlnet_image_name 已上传的深度控制图文件名
    @param controlnet_strength ControlNet 强度
    @return ComfyUI API workflow
    """
    path = template_path or _workflow_template_path(workflow_name)
    workflow = load_workflow_template(path)
    workflow["prompt"]["5"]["inputs"]["text"] = prompt
    workflow["prompt"]["8"]["inputs"]["seed"] = seed
    workflow["prompt"]["10"]["inputs"]["filename_prefix"] = filename_prefix

    if workflow_name == WORKFLOW_DEPTH:
        if controlnet_image_name:
            workflow["prompt"]["12"]["inputs"]["image"] = controlnet_image_name
        if controlnet_strength is not None:
            workflow["prompt"]["13"]["inputs"]["strength"] = controlnet_strength
    return workflow
