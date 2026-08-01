"""即梦 AI API 客户端(AK/SK 签名,异步两段式)
官方文档: docs.volcengine.com/docs/85621
提交: POST visual.volcengineapi.com?Action=CVSync2AsyncSubmitTask&Version=2022-08-31
查询: Action=CVSync2AsyncGetResult
"""
import base64
import time

import requests
from volcengine.visual.VisualService import VisualService

from app.config import config

# 固定值(官方文档):Region=cn-north-1, Service=cv
service = VisualService()
service.set_ak(config.JIMENG_ACCESS_KEY)
service.set_sk(config.JIMENG_SECRET_KEY)
service.set_host("visual.volcengineapi.com")


def _submit(req_key: str, body: dict) -> str:
    """提交异步任务,返回 task_id"""
    payload = {"req_key": req_key, **body}
    resp = service.CVSync2AsyncSubmitTask(payload)
    code = resp.get("code")
    if code != 10000:
        raise RuntimeError(f"即梦提交失败 code={code} msg={resp.get('message')} resp={resp}")
    return resp["data"]["task_id"]


def _poll(task_id: str, req_key: str, timeout: int = 300, interval: int = 3) -> dict:
    """轮询任务结果,返回 data(含 image_urls 或 binary_data_base64)"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = service.CVSync2AsyncGetResult({
            "req_key": req_key,
            "task_id": task_id,
        })
        code = resp.get("code")
        if code != 10000:
            raise RuntimeError(f"即梦查询失败 code={code} msg={resp.get('message')}")
        data = resp.get("data", {})
        status = data.get("status")
        if status == "done":
            return data
        if status in ("failed", "expired", "not_found"):
            raise RuntimeError(f"即梦任务异常 status={status} data={data}")
        time.sleep(interval)
    raise TimeoutError(f"即梦任务超时 task_id={task_id}")


def background_replace(upload_b64: str, prompt: str, seg_prompt: str = "") -> dict:
    """AI营销商品图3.0:背景替换。req_key: i2i_dreamlight3_0_background_replace"""
    body = {
        "binary_data_base64": [upload_b64],
        "prompt": prompt,
    }
    if seg_prompt:
        body["seg_prompt"] = seg_prompt
    tid = _submit("i2i_dreamlight3_0_background_replace", body)
    return _poll(tid, "i2i_dreamlight3_0_background_replace")


def extract_product(upload_b64: str, edit_prompt: str = "提取日用品") -> dict:
    """素材提取·商品提取:抠商品生成白底图。req_key: jimeng_i2i_extract_tiled_images"""
    body = {
        "binary_data_base64": [upload_b64],
        "edit_prompt": edit_prompt,
        "width": 1024,
        "height": 1024,
    }
    tid = _submit("jimeng_i2i_extract_tiled_images", body)
    return _poll(tid, "jimeng_i2i_extract_tiled_images")


def generate_multi(upload_b64s: list, prompt: str, size: int = 1024) -> dict:
    """图片生成4.6:多参考图生成。req_key: jimeng_seedream46_cvtob
    size 默认 4194304(2042²);force_single=true 每次只出 1 张"""
    body = {
        "binary_data_base64": upload_b64s,
        "prompt": prompt,
        "size": size,
        "force_single": True,
    }
    tid = _submit("jimeng_seedream46_cvtob", body)
    return _poll(tid, "jimeng_seedream46_cvtob")


def decode_result(data: dict) -> list:
    """把即梦返回结果转成本地图片 bytes 列表(优先 base64,其次下载 URL)"""
    images = []
    if data.get("binary_data_base64"):
        for b64 in data["binary_data_base64"]:
            images.append(base64.b64decode(b64))
    elif data.get("image_urls"):
        for url in data["image_urls"]:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            images.append(r.content)
    return images
