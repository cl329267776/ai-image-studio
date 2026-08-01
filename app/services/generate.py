"""生成编排:主图 + 详情图"""
import base64
import os

from app.api.factory import get_client
from app.services import postprocess

# 5 张主图的风格提示词(1688 TO B 纸罐行业,见调研附录)
# 提示词统一:圆柱形纸罐、真实产品摄影、电商主图、无文字(避免 AI 乱码文字)
MAIN_PROMPTS = [
    "纯白色背景的商品摄影图,圆柱形纸罐主体居中,真实质感,电商主图",          # 第1张:白底(商品提取API做,此条备用)
    "简约商务场景,浅灰台面,自然光,圆柱形纸罐,专业商品摄影,电商主图",          # 第2张:商务场景
    "深色背景高端质感,侧面光,突出纸罐材质纹理和卷边工艺,真实摄影,电商主图",   # 第3张:材质细节
    "简洁明亮背景,圆柱形纸罐完整展示,突出可定制印刷罐身,真实摄影,电商主图",   # 第4张:定制展示
    "45度角展示完整纸罐形态,柔和渐变背景,真实产品摄影,电商主图",              # 第5张:45度
]


def _b64(path: str) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def generate(task: dict, custom_prompt: str = "") -> dict:
    """执行完整生成流程,返回结果 dict
    task: Task 3 的 save_upload 返回 dict
    """
    client = get_client()
    upload_b64 = _b64(task["upload_path"])
    results = {"main_images": [], "detail_images": [], "errors": []}

    # --- 主图 ---
    # 第 1 张:商品提取(白底抠图)→ 直接 800×800
    try:
        imgs = client.extract_product(upload_b64)
        if imgs:
            p1 = os.path.join(task["main_dir"], "主图1_白底.jpg")
            with open(p1, "wb") as f:
                f.write(postprocess.to_square_800(imgs[0]))
            results["main_images"].append(p1)
    except Exception as e:
        results["errors"].append(f"主图1白底失败: {e}")

    # 第 2-5 张:背景替换(4 种风格)
    prompts = MAIN_PROMPTS[1:] if not custom_prompt else [custom_prompt] * 4
    for i, p in enumerate(prompts, start=2):
        try:
            imgs = client.background_replace(upload_b64, p)
            if imgs:
                fn = os.path.join(task["main_dir"], f"主图{i}_{p[:6]}.jpg")
                with open(fn, "wb") as f:
                    f.write(postprocess.to_square_800(imgs[0]))
                results["main_images"].append(fn)
        except Exception as e:
            results["errors"].append(f"主图{i}失败: {e}")

    # --- 详情图(九宫格)---
    # 素材:白底图 + 4 张风格化主图 + 原图,凑 9 格
    cells = []
    if results["main_images"]:
        for p in results["main_images"]:
            with open(p, "rb") as f:
                cells.append(f.read())
    while len(cells) < 9:
        cells.append(cells[0] if cells else upload_b64.encode())
    cells = cells[:9]
    try:
        grid = postprocess.make_grid(cells)
        d1 = os.path.join(task["detail_dir"], "详情图1_九宫格.jpg")
        with open(d1, "wb") as f:
            f.write(grid)
        results["detail_images"].append(d1)
    except Exception as e:
        results["errors"].append(f"详情图1失败: {e}")

    # 第 2 张详情图:换一种排列(不同顺序)
    try:
        cells2 = cells[1:] + cells[:1]
        grid2 = postprocess.make_grid(cells2)
        d2 = os.path.join(task["detail_dir"], "详情图2_九宫格.jpg")
        with open(d2, "wb") as f:
            f.write(grid2)
        results["detail_images"].append(d2)
    except Exception as e:
        results["errors"].append(f"详情图2失败: {e}")

    return results
