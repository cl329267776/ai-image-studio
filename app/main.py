"""FastAPI 入口:上传 → 生成 → 轮询 → 下载"""
import json
import os
import threading
import traceback
from typing import List

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import config
from app import prompts as prompts_mod
from app.services import generate
from app.storage import list_tasks, save_uploads

app = FastAPI(title="AI 商品图生成工具")

# 任务状态(内存版,单用户够用;重启丢失可接受)
TASKS: dict[str, dict] = {}

app.mount("/static", StaticFiles(directory=os.path.join(config.BASE_DIR, "app/static")), name="static")
app.mount("/outputs", StaticFiles(directory=config.OUTPUT_DIR), name="outputs")


class GenerateRequest(BaseModel):
    custom_prompt: str = ""


@app.get("/")
def index():
    return FileResponse(os.path.join(config.BASE_DIR, "app/static/index.html"))


@app.get("/api/prompts")
def get_prompts():
    """读取提示词(main[5] + detail[2])"""
    return prompts_mod.load_prompts()


@app.post("/api/prompts")
async def save_prompts(body: dict):
    """保存提示词,body: {"main": [...], "detail": [...]}"""
    main = body.get("main")
    detail = body.get("detail")
    if not isinstance(main, list) or len(main) < 5:
        return JSONResponse({"error": "main 需为长度≥5的数组"}, status_code=400)
    if not isinstance(detail, list) or len(detail) < 2:
        return JSONResponse({"error": "detail 需为长度≥2的数组"}, status_code=400)
    prompts_mod.save_prompts({"main": main, "detail": detail})
    return {"ok": True}


@app.post("/api/upload")
async def upload(files: List[UploadFile] = File(...), prompts: str = Form("")):
    """上传 1~9 张原图,立即返回 task_id(生成在后台线程跑)

    files: 全部原图(作为 AI 参考图)
    prompts: JSON 字符串 {"main": [...], "detail": [...]},留空则用服务器默认
    """
    if not files:
        return JSONResponse({"error": "请选择至少一张原图"}, status_code=400)
    if len(files) > 9:
        return JSONResponse({"error": "最多上传 9 张原图"}, status_code=400)

    file_list = [(await f.read(), f.filename or f"upload_{i}.jpg")
                 for i, f in enumerate(files, start=1)]
    task = save_uploads(file_list)
    task["status"] = "pending"
    task["custom_prompt"] = ""
    # 解析前端传来的提示词;非法 JSON 或为空 → None(用服务器默认)
    try:
        task["prompts"] = json.loads(prompts) if prompts else None
    except json.JSONDecodeError:
        task["prompts"] = None
    task["results"] = {}
    task["error"] = ""
    TASKS[task["task_id"]] = task

    def worker():
        try:
            task["status"] = "generating"
            results = generate.generate(task, task["prompts"])
            task["results"] = results
            task["status"] = "done" if results["main_images"] or results["detail_images"] else "partial"
            if results["errors"]:
                task["error"] = "；".join(results["errors"])
        except Exception as e:
            task["status"] = "failed"
            task["error"] = f"{e}\n{traceback.format_exc()}"

    threading.Thread(target=worker, daemon=True).start()
    return {"task_id": task["task_id"]}


@app.get("/api/task/{task_id}")
def get_task(task_id: str):
    """查询任务进度与结果"""
    task = TASKS.get(task_id)
    if not task:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "task_id": task_id,
        "status": task["status"],
        "error": task["error"],
        "main_images": [os.path.basename(p) for p in task["results"].get("main_images", [])],
        "detail_images": [os.path.basename(p) for p in task["results"].get("detail_images", [])],
        "task_dir": task["task_dir"],
    }


@app.get("/api/tasks")
def tasks():
    """历史任务列表"""
    return {"tasks": list_tasks()}


@app.get("/outputs/{date}/{tid}/{fname}")
def get_file(date: str, tid: str, fname: str):
    """预览/下载生成图(实际由 StaticFiles 处理,这里兜底)"""
    path = os.path.join(config.OUTPUT_DIR, date, tid, fname)
    if os.path.isfile(path):
        return FileResponse(path)
    return JSONResponse({"error": "not found"}, status_code=404)
