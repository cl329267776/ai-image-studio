"""方舟 Doubao Seedream 5.0 客户端(备选通道,同步返回)
官方文档: docs.volcengine.com/docs/82379/1541523
POST https://ark.cn-beijing.volces.com/api/v3/images/generations
能力:文生图/单图生图/多图生图(2-14 参考图);参考图+输出 ≤15 张
"""
import base64

import requests

from app.config import config

ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"
# 5.0 pro(默认)/ lite / 4.5 / 4.0 可切换
MODEL = "doubao-seedream-5-0-pro-260628"


def _data_url(b64: str) -> str:
    """参考图是压缩后的 JPEG → data URL 用 jpeg 前缀"""
    return f"data:image/jpeg;base64,{b64}"


def _call(prompt: str, image_b64: str | None = None, size: str = "1024x1024",
          n: int = 1, ref_b64s: list | None = None) -> list:
    """同步生成,返回图片 bytes 列表
    image: 单图(字符串 data URL)或多图(数组);watermark 关掉避免 AI 水印
    """
    if not config.ARK_API_KEY:
        raise RuntimeError("未配置方舟 API Key: 请在 .env 填 ARK_API_KEY(sk-xxx)")
    headers = {"Authorization": f"Bearer {config.ARK_API_KEY}"}
    payload: dict = {
        "model": MODEL,
        "prompt": prompt,
        "size": size,
        "n": n,
        "response_format": "b64_json",
        "watermark": False,
    }
    if ref_b64s:
        payload["image"] = [_data_url(b) for b in ref_b64s]  # 多参考图(数组)
    elif image_b64:
        payload["image"] = _data_url(image_b64)              # 单参考图(字符串)
    resp = requests.post(ENDPOINT, json=payload, headers=headers, timeout=180)
    if resp.status_code != 200:
        raise RuntimeError(f"方舟请求失败 HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return [base64.b64decode(item["b64_json"]) for item in data["data"]]


def background_replace(upload_b64: str, prompt: str, seg_prompt: str = "") -> list:
    """图生图换背景(单参考图)"""
    return _call(prompt, image_b64=upload_b64)


def extract_product(upload_b64: str, edit_prompt: str = "提取日用品") -> list:
    """抠商品白底图(方舟无专门抠图接口,用图生图近似)"""
    return _call(f"白底商品图,纯白背景,产品完整展示,{edit_prompt}", image_b64=upload_b64)


def generate_multi(ref_b64s: list, prompt: str, n: int = 1,
                   size: str = "1024x1024") -> list:
    """多参考图生成 n 张(方舟支持多图生图,一次返回 n 张,同步)"""
    return _call(prompt, ref_b64s=ref_b64s, n=n, size=size)
