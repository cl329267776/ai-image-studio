"""生成编排:主图(5 张)+ 详情图(1 AI 详情页 + 1 九宫格)

提示词来源:prompts.json(默认从 ai-images.txt 摘取,页面可独立编辑保存)
参考图:全部上传原图(multi-reference,即梦图片生成4.6 支持 0-14 张)
"""
import base64
import os
import time

from app.api.factory import get_client
from app import prompts as prompts_mod
from app.services import postprocess


def _b64(path: str) -> str:
    """读图并压缩(最长边≤1024,JPEG q85)后 base64。

    必须压缩:即梦网关对请求体大小有限制,多张手机原图(3072×4096, 2-3MB/张)
    base64 后总请求体可达 20-30MB,触发 'Error when parsing request'。
    压缩后单张约 150-300KB,8 张合计 <3MB,稳定通过。
    """
    from PIL import Image
    import io
    with Image.open(path) as img:
        img = img.convert("RGB")
        if max(img.size) > 1024:
            img.thumbnail((1024, 1024), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return base64.b64encode(buf.getvalue()).decode()


def _get_uploads(task: dict) -> list:
    """取上传原图路径列表(兼容多文件 uploads 与旧单文件 upload_path)"""
    uploads = task.get("uploads")
    if uploads:
        return [u["upload_path"] for u in uploads]
    if task.get("upload_path"):
        return [task["upload_path"]]
    return []


def generate(task: dict, prompts: dict | None = None) -> dict:
    """执行完整生成流程,返回结果 dict
    task: save_uploads 返回 dict
    prompts: {"main": [5], "detail": [2]},None 则用服务器默认(prompts.json)
    """
    client = get_client()
    if prompts is None:
        prompts = prompts_mod.load_prompts()

    upload_paths = _get_uploads(task)
    if not upload_paths:
        return {"main_images": [], "detail_images": [], "errors": ["未找到上传原图"]}

    ref_b64s = [_b64(p) for p in upload_paths]
    main_prompts = prompts.get("main", [])
    detail_prompts = prompts.get("detail", [])
    results = {"main_images": [], "detail_images": [], "errors": []}

    # --- 主图 ---
    # 第 1 张:商品提取(白底抠图,该 API 只收 1 张 → 用第 1 张原图)
    try:
        imgs = client.extract_product(ref_b64s[0])
        if imgs:
            p1 = os.path.join(task["main_dir"], "主图1_白底.jpg")
            with open(p1, "wb") as f:
                f.write(postprocess.to_square_800(imgs[0]))
            results["main_images"].append(p1)
    except Exception as e:
        results["errors"].append(f"主图1白底失败: {e}")

    # 第 2-5 张:图片生成4.6 多参考图 + 各自独立提示词(缺省用默认第 2-5 条)
    for i in range(1, 5):
        p = main_prompts[i] if len(main_prompts) > i else ""
        try:
            imgs = client.generate_multi(ref_b64s, p, n=1)
            if imgs:
                fn = os.path.join(task["main_dir"], f"主图{i+1}.jpg")
                with open(fn, "wb") as f:
                    f.write(postprocess.to_square_800(imgs[0]))
                results["main_images"].append(fn)
        except Exception as e:
            results["errors"].append(f"主图{i+1}失败: {e}")
        # 免费并发只有 1:上一张 done 后服务端并发释放有延迟,间隔 3s 降低碰撞
        time.sleep(3)

    # --- 详情图 ---
    # 详情图 1:AI 生成 6 区域详情页(图片生成4.6 多参考图,detail[0] 提示词)
    # 注:竖版 width/height(1024×1536)在免费并发下会卡服务端队列(实测 17min+ 不结束),
    # 暂用方形 size=1048576(1024²),后处理缩到宽 800;竖版等付费并发后再优化
    d0_prompt = detail_prompts[0] if detail_prompts else ""
    if d0_prompt:
        try:
            imgs = client.generate_multi(ref_b64s, d0_prompt, n=1)
            if imgs:
                d1 = os.path.join(task["detail_dir"], "详情图1_AI详情页.jpg")
                with open(d1, "wb") as f:
                    f.write(postprocess.to_width_800(imgs[0]))
                results["detail_images"].append(d1)
        except Exception as e:
            results["errors"].append(f"详情图1失败: {e}")

    # 详情图 2:本地 Pillow 九宫格(素材:白底图 + 风格化主图,凑 9 格)
    cells = []
    if results["main_images"]:
        for p in results["main_images"]:
            with open(p, "rb") as f:
                cells.append(f.read())
    while len(cells) < 9:
        cells.append(cells[0] if cells else open(upload_paths[0], "rb").read())
    cells = cells[:9]
    try:
        grid = postprocess.make_grid(cells)
        d2 = os.path.join(task["detail_dir"], "详情图2_九宫格.jpg")
        with open(d2, "wb") as f:
            f.write(grid)
        results["detail_images"].append(d2)
    except Exception as e:
        results["errors"].append(f"详情图2失败: {e}")

    return results
