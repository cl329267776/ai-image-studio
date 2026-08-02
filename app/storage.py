import os
import uuid
from datetime import datetime

from app.config import config


def date_dir() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def save_upload(file_bytes: bytes, filename: str) -> dict:
    """保存上传原图(单文件),返回 {path, url, task_dir}"""
    return save_uploads([(file_bytes, filename)])


def save_uploads(file_list: list[tuple[bytes, str]]) -> dict:
    """保存多张上传原图到同一任务目录,返回 task dict(含 uploads list)

    file_list: [(file_bytes, filename), ...],至少 1 个
    uploads 元素: {"upload_path": ..., "filename": 原始文件名, "index": 序号}
    """
    if not file_list:
        raise ValueError("file_list 不能为空")
    task_id = uuid.uuid4().hex[:12]
    task_dir = os.path.join(config.OUTPUT_DIR, date_dir(), task_id)
    main_dir = os.path.join(task_dir, "主图")
    detail_dir = os.path.join(task_dir, "详情图")
    os.makedirs(main_dir, exist_ok=True)
    os.makedirs(detail_dir, exist_ok=True)

    uploads = []
    for idx, (file_bytes, filename) in enumerate(file_list, start=1):
        safe_name = os.path.basename(filename) or f"upload_{idx}.jpg"
        upload_path = os.path.join(task_dir, f"原图_{idx}_{safe_name}")
        with open(upload_path, "wb") as f:
            f.write(file_bytes)
        uploads.append({
            "upload_path": upload_path,
            "filename": safe_name,
            "index": idx,
        })
    return {
        "task_id": task_id,
        "task_dir": task_dir,
        "main_dir": main_dir,
        "detail_dir": detail_dir,
        "uploads": uploads,
        # 兼容旧字段:单文件时 upload_path 指向第一张
        "upload_path": uploads[0]["upload_path"],
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
