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


def _submit(req_key: str, body: dict, retries: int = 60) -> str:
    """提交异步任务,返回 task_id

    免费试用并发只有 1:多任务会撞 50430(并发超限)/50429(QPS 超限)。
    这是「排队中」信号而不是致命错误 —— 服务端队列消化后会自动放行,
    所以长时重试(默认 60 次 × 10s 间隔 ≈ 10 分钟),期间不判失败。
    SDK 对非 10000 响应会抛异常(异常消息里带 code),需解析 code 判断。
    """
    payload = {"req_key": req_key, **body}
    for attempt in range(retries):
        resp = None
        try:
            resp = service.cv_sync2async_submit_task(payload)
        except Exception as e:
            msg = str(e)
            # SDK 抛异常时从消息里解析 code(如 b'{"code":50430,...}')
            import re
            m = re.search(r'"code"\s*:\s*(\d+)', msg)
            code = int(m.group(1)) if m else None
            if code in (50430, 50429):
                print(f"[即梦] 并发/QPS 排队中(code={code}),第 {attempt+1}/{retries} 次,等待 10s")
                time.sleep(10)
                continue
            raise RuntimeError(f"即梦提交异常(请求被网关拒绝): {msg}")
        code = resp.get("code")
        if code == 10000:
            return resp["data"]["task_id"]
        if code in (50430, 50429):
            print(f"[即梦] 并发/QPS 排队中(code={code}),第 {attempt+1}/{retries} 次,等待 10s")
            time.sleep(10)
            continue
        raise RuntimeError(f"即梦提交失败 code={code} msg={resp.get('message')} resp={resp}")
    raise RuntimeError(f"即梦提交等待 {retries*10}s 仍无法进入队列(并发持续被占)")


def _poll(task_id: str, req_key: str, timeout: int = 600, interval: int = 3) -> dict:
    """轮询任务结果,返回 data(含 image_urls 或 binary_data_base64)"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = service.cv_sync2async_get_result({
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


def generate_multi(upload_b64s: list, prompt: str, size: int = 1048576,
                   width: int = 0, height: int = 0) -> dict:
    """图片生成4.6:多参考图生成。req_key: jimeng_seedream46_cvtob
    size 为面积,合法范围 [1024*1024, 4096*4096](默认 1048576=1024²,1K)
    传 width/height 时用宽高(宽高积同样须在合法范围,竖版详情页用)
    force_single=true 每次只出 1 张"""
    body = {
        "binary_data_base64": upload_b64s,
        "prompt": prompt,
        "force_single": True,
    }
    if width and height:
        body["width"] = width
        body["height"] = height
    else:
        body["size"] = size
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
