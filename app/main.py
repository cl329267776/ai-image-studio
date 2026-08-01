"""FastAPI 入口:上传 → 生成 → 轮询 → 下载"""
import os
import threading
import traceback

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import config
from app.services import generate
from app.storage import list_tasks, save_upload

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


@app.post("/api/upload")
async def upload(file: UploadFile = File(...), custom_prompt: str = Form("")):
    """上传原图,立即返回 task_id(生成在后台线程跑)"""
    data = await file.read()
    task = save_upload(data, file.filename or "upload.jpg")
    task["status"] = "pending"
    task["custom_prompt"] = custom_prompt
    task["results"] = {}
    task["error"] = ""
    TASKS[task["task_id"]] = task

    def worker():
        try:
            task["status"] = "generating"
            results = generate.generate(task, custom_prompt)
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
