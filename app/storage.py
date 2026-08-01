import os
import uuid
from datetime import datetime

from app.config import config


def date_dir() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def save_upload(file_bytes: bytes, filename: str) -> dict:
    """保存上传原图,返回 {path, url, task_dir}"""
    task_id = uuid.uuid4().hex[:12]
    task_dir = os.path.join(config.OUTPUT_DIR, date_dir(), task_id)
    main_dir = os.path.join(task_dir, "主图")
    detail_dir = os.path.join(task_dir, "详情图")
    os.makedirs(main_dir, exist_ok=True)
    os.makedirs(detail_dir, exist_ok=True)

    safe_name = os.path.basename(filename) or "upload.jpg"
    upload_path = os.path.join(task_dir, "原图_" + safe_name)
    with open(upload_path, "wb") as f:
        f.write(file_bytes)
    return {
        "task_id": task_id,
        "task_dir": task_dir,
        "main_dir": main_dir,
        "detail_dir": detail_dir,
        "upload_path": upload_path,
    }


def list_tasks() -> list:
    """列出所有任务(按日期目录扫描)"""
    tasks = []
    if not os.path.isdir(config.OUTPUT_DIR):
        return tasks
    for day in sorted(os.listdir(config.OUTPUT_DIR), reverse=True):
        day_path = os.path.join(config.OUTPUT_DIR, day)
        if not os.path.isdir(day_path):
            continue
        for tid in sorted(os.listdir(day_path), reverse=True):
            tpath = os.path.join(day_path, tid)
            if os.path.isdir(tpath):
                tasks.append({"date": day, "task_id": tid, "path": tpath})
    return tasks
