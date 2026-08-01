"""通道适配器:jimeng(异步,返回 dict 需轮询) vs ark(同步,返回 list bytes)"""
from app.config import config

from . import ark_client, jimeng_client


class ClientAdapter:
    def __init__(self, provider: str):
        self.provider = provider

    def background_replace(self, upload_b64: str, prompt: str, seg_prompt: str = ""):
        """返回图片 bytes 列表"""
        if self.provider == "ark":
            return ark_client.background_replace(upload_b64, prompt)
        data = jimeng_client.background_replace(upload_b64, prompt, seg_prompt)
        return jimeng_client.decode_result(data)

    def extract_product(self, upload_b64: str, edit_prompt: str = "提取日用品"):
        """抠商品白底图,返回 bytes 列表"""
        if self.provider == "ark":
            return ark_client.background_replace(upload_b64, f"白底商品图,{edit_prompt}")
        data = jimeng_client.extract_product(upload_b64, edit_prompt)
        return jimeng_client.decode_result(data)

    def generate_multi(self, ref_b64s: list, prompt: str, n: int = 1):
        """多参考图生成 n 张,返回 bytes 列表"""
        if self.provider == "ark":
            return ark_client.generate_multi(ref_b64s, prompt, n=n)
        # jimeng: 每张一次 force_single 调用(并发受限于平台,先串行)
        images = []
        for _ in range(n):
            data = jimeng_client.generate_multi(ref_b64s, prompt)
            images.extend(jimeng_client.decode_result(data))
        return images


def get_client() -> ClientAdapter:
    return ClientAdapter(config.API_PROVIDER)
