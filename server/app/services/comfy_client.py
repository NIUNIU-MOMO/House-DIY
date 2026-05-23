import copy
import json
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.core.config import settings

DEFAULT_WORKFLOW_PATH = (
    Path(__file__).resolve().parents[3] / "workflows" / "room_render_api.json"
)


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

    def get_history(self, prompt_id: str) -> dict[str, Any]:
        response = self._client.get(f"/history/{prompt_id}")
        response.raise_for_status()
        return response.json()

    def wait_for_completion(
        self,
        prompt_id: str,
        poll_interval: float = 2.0,
        timeout: float = 600.0,
    ) -> dict[str, Any]:
        """
        轮询等待 ComfyUI 任务完成

        @param prompt_id 任务 ID
        @param poll_interval 轮询间隔秒
        @param timeout 超时秒
        @return history 条目
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            history = self.get_history(prompt_id)
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(poll_interval)
        raise TimeoutError(f"ComfyUI prompt {prompt_id} timed out")

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


def build_room_render_workflow(
    prompt: str,
    seed: int,
    filename_prefix: str,
    template_path: Path | None = None,
) -> dict[str, Any]:
    """
    构建参数化房间渲染 workflow

    @param prompt 正向提示词
    @param seed 随机种子
    @param filename_prefix 输出前缀
    @param template_path 模板路径
    @return ComfyUI API workflow
    """
    workflow = load_workflow_template(template_path)
    workflow["prompt"]["5"]["inputs"]["text"] = prompt
    workflow["prompt"]["8"]["inputs"]["seed"] = seed
    workflow["prompt"]["10"]["inputs"]["filename_prefix"] = filename_prefix
    return workflow
