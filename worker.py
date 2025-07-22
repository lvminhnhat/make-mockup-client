import time
import requests
import os
import logging
from utils.task_utils import *
from models.task import Base_task  # Không dùng object này để thao tác task, vẫn xử lý dict
from utils.load_config import ConfigLoader
from lib.photoshop_automation import PhotoshopAutomation
from image_procesing import process_task


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add file handler for error logs
error_handler = logging.FileHandler('error.log')
error_handler.setLevel(logging.ERROR)
error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
error_handler.setFormatter(error_formatter)
logger.addHandler(error_handler)

config_loader = ConfigLoader()

def get_task():
    server_url = config_loader.get_config_value("app.server_url", "http://localhost:8000")
    client_name = config_loader.get_config_value('app.client_name', 'default_client_name')
    task_json_url = f"{server_url}/{client_name}/pending-longest/"
    
    for _ in range(3):  # Retry tối đa 3 lần
        try:
            response = requests.get(task_json_url, timeout=10)
            if response.status_code == 200:
                response_data = response.json()
                image_url = response_data.get("image_url")
                image_path = None
                if image_url:
                    image_url_full = (
                        server_url.rstrip("/") + image_url if image_url.startswith("/") else image_url
                    )
                    os.makedirs("downloads", exist_ok=True)
                    file_name = os.path.basename(image_url)
                    image_path = os.path.join("downloads", file_name)
                    img_resp = requests.get(image_url_full, stream=True, timeout=10)
                    if img_resp.status_code == 200:
                        with open(image_path, "wb") as f:
                            for chunk in img_resp.iter_content(1024):
                                f.write(chunk)
                        logger.info(f"Downloaded image from {image_url_full} to {image_path}")
                    else:
                        logger.warning(f"Failed to download image: {image_url_full} (status {img_resp.status_code})")
                response_data["downloaded_image_path"] = image_path
                return response_data
            else:
                if response.status_code == 404:
                    logger.info("No tasks found, waiting for new tasks...")
                    return None
                logger.warning(f"Failed to get task ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"Exception in get_task: {e}")
        time.sleep(2)
    return None

def update_task(task: dict, image_paths: list = []):
    server_url = config_loader.get_config_value("app.server_url", "http://localhost:8000")
    client_name = config_loader.get_config_value('app.client_name', 'default_client_name')
    update_url = f"{server_url}/{client_name}/update-task/"

    data = {
        "id": task.get("id"),
        "status": task.get("status"),
        "message": task.get("message")
    }

    files = []
    for img_path in image_paths:
        if os.path.isfile(img_path):
            files.append(("images", (os.path.basename(img_path), open(img_path, "rb"), "image/png")))
        else:
            logger.warning(f"File not found: {img_path}")

    try:
        response = requests.patch(update_url, data=data, files=files, timeout=15)
        for _, file_tuple in files:
            file_tuple[1].close()
        if response.status_code == 200:
            logger.info(f"Task {task.get('id')} updated successfully.")
            return response.json()
        else:
            logger.error(f"Failed to update task {task.get('id')}: {response.status_code} {response.text}")
            return None
    except Exception as e:
        logger.error(f"Exception in update_task: {e}")
    return None

def worker_loop():
    while True:
        task = get_task()
        #print(f"[PTS] Đã nhận task: {task}")
        if not task:
            logger.info("No tasks found, waiting for new tasks...")
            time.sleep(5)
            continue

        status = task.get("status", "pending")
        task_id = task.get("id", "unknown")
        new_task = Base_task.from_dict(task)
        if status == "pending":
            logger.info(f"Processing task: {task_id}")
            try:
                # Gọi process_task, trả về list đường dẫn file ảnh kết quả
                final_images = process_task(new_task) or []
                if isinstance(final_images, str):
                    final_images = [final_images]
                task["status"] = "completed"
                task["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                task["message"] = "Completed"
                logger.info(f"Task {task_id} completed successfully.")
            except Exception as e:
                logger.error(f"Error processing {task_id}: {e}")
                task["status"] = "failed"
                task["message"] = str(e)
                final_images = []
        else:
            logger.info(f"Task {task_id} has status {status}, skip processing.")
            final_images = []
        print(final_images)
        check = update_task(task, final_images)
        if check:
            logger.info(f"Task {task_id} updated with status {task['status']}.")
        else:
            logger.error(f"Failed to update task {task_id}.")
        time.sleep(5)

if __name__ == "__main__":
    logger.info("Worker started.")
    worker_loop()
