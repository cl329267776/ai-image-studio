"""方舟 Doubao Seedream 5.0 客户端(备选通道)
官方文档: docs.volcengine.com/docs/82379/1541523
POST https://ark.cn-beijing.volces.com/api/v3/images/generations
"""
import base64

import requests

from app.config import config

ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
MODEL = "doubao-seedream-5-0-pro-260628"


def _call(prompt: str, image_b64: str | None = None, size: str = "1024x1024",
          n: int = 1, ref_b64s: list | None = None) -> list:
    """同步生成,返回图片 bytes 列表"""
    headers = {"Authorization": f"Bearer {config.ARK_API_KEY}"}
    payload: dict = {
        "model": MODEL,
        "prompt": prompt,
        "size": size,
        "n": n,
        "response_format": "b64_json",
    }
    if ref_b64s:
        payload["image"] = [f"data:image/png;base64,{b}" for b in ref_b64s]
    elif image_b64:
        payload["image"] = f"data:image/png;base64,{image_b64}"
    resp = requests.post(ENDPOINT, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return [base64.b64decode(item["b64_json"]) for item in data["data"]]


def background_replace(upload_b64: str, prompt: str) -> list:
    """图生图换背景(单参考图)"""
    return _call(prompt, image_b64=upload_b64)


def generate_multi(ref_b64s: list, prompt: str, n: int = 5) -> list:
    """多参考图生成 n 张"""
    return _call(prompt, ref_b64s=ref_b64s, n=n)
