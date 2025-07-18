import json
from typing import List, Dict, Any
from utils.parse_util import parse_time_delta
from models.task import Base_task
from datetime import datetime 



def read_tasks(file_path: str) -> List[Base_task]:
    """Đọc danh sách task từ file JSON. Nếu file không tồn tại hoặc rỗng trả về list rỗng."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [Base_task.from_dict(item) for item in data]
            return []
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def write_tasks(file_path: str, tasks: List[Base_task]) -> None:
    """Merge các task mới với task cũ, ưu tiên task mới nếu trùng id."""
    current_tasks = read_tasks(file_path)
    task_dict = {task.id: task for task in current_tasks}
    for task in tasks:
        task_dict[task.id] = task
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump([task.to_dict() for task in task_dict.values()], f, ensure_ascii=False, indent=2)


def clear_tasks(file_path: str, period : str):
    """
    Xoá các task đã quá hạn dựa trên khoảng thời gian cho trước.
    
    Args:
        file_path: Đường dẫn đến file chứa danh sách task.
        period: Khoảng thời gian để xác định task nào cần xoá (ví dụ: '1w', '2d').

    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0
    # Tính mốc thời gian cutoff
    cutoff_time = datetime.now() - parse_time_delta(period)
    kept_tasks: List[dict] = []
    removed = 0

    for task in data:
        try:
            created_dt = datetime.fromisoformat(task["created_at"])
            if created_dt >= cutoff_time:
                kept_tasks.append(task)
            else:
                removed += 1
        except Exception:
            # Không đọc được ngày tạo, giữ lại (hoặc có thể cho auto xóa)
            kept_tasks.append(task)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(kept_tasks, f, ensure_ascii=False, indent=2)
    return removed