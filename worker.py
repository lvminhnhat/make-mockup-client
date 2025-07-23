# worker.py
import time
import requests
import os
import logging
import json
from datetime import datetime
from utils.task_utils import *
from models.task import Base_task
from utils.load_config import ConfigLoader
from utils.enhanced_logger_manager import enhanced_logger_manager  # Import logger manager
from lib.photoshop_automation import PhotoshopAutomation
from image_procesing import process_task

# Use the logger configured by logger_manager
# It's generally better practice to get the logger specific to this module
# rather than relying on __name__ if the manager sets up a specific one.
# If logger_manager provides a specific logger instance, use that.
# For now, assuming it configures the root logger or one accessible via getLogger(__name__)
logger = logging.getLogger(__name__) 
config_loader = ConfigLoader()

# --- get_task function remains largely the same ---
def get_task():
    """Lấy task từ server với logging chi tiết"""
    server_url = config_loader.get_config_value("app.server_url", "http://localhost:8000")
    client_name = config_loader.get_config_value('app.client_name', 'default_client_name')
    task_json_url = f"{server_url}/{client_name}/pending-longest/"
    logger.info(f"🔍 Requesting task from: {task_json_url}")

    for attempt in range(3):  # Retry tối đa 3 lần
        try:
            logger.info(f"📡 Attempt {attempt + 1}/3 to get task")
            response = requests.get(task_json_url, timeout=10)
            if response.status_code == 200:
                response_data = response.json()
                task_id = response_data.get("id", "unknown")
                logger.info(f"✅ Task received: ID={task_id}")

                # Download image nếu có
                image_url = response_data.get("image_url")
                image_path = None
                if image_url:
                    logger.info(f"📥 Downloading image from: {image_url}")
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
                        file_size = os.path.getsize(image_path)
                        logger.info(f"✅ Image downloaded: {image_path} ({file_size:,} bytes)")
                    else:
                        logger.warning(f"❌ Failed to download image: {image_url_full} (status {img_resp.status_code})")

                response_data["downloaded_image_path"] = image_path
                return response_data

            elif response.status_code == 404:
                logger.info("📭 No tasks found, waiting for new tasks...")
                return None
            else:
                logger.warning(f"⚠️ Failed to get task ({response.status_code}): {response.text}")

        except requests.exceptions.Timeout:
            logger.error(f"⏰ Timeout on attempt {attempt + 1}")
        except requests.exceptions.ConnectionError:
            logger.error(f"🔌 Connection error on attempt {attempt + 1}")
        except Exception as e:
            logger.error(f"💥 Exception in get_task (attempt {attempt + 1}): {e}", exc_info=True) # Add exc_info

        if attempt < 2:  # Không sleep ở lần cuối
            logger.info("⏳ Waiting 2 seconds before retry...")
            time.sleep(2)

    logger.error("💥 All attempts failed to get task")
    return None

# --- send_logs_to_server function remains largely the same ---
def send_logs_to_server(task_id: str, log_data: dict):
    """Gửi logs về server"""
    server_url = config_loader.get_config_value("app.server_url", "http://localhost:8000")
    client_name = config_loader.get_config_value('app.client_name', 'default_client_name')
    log_url = f"{server_url}/{client_name}/task-logs/"

    try:
        logger.info(f"📤 Sending logs for task {task_id} to server")
        payload = {
            "task_id": task_id,
            "client_name": client_name,
            "log_data": log_data
        }
        response = requests.post(
            log_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )
        if response.status_code == 200:
            logger.info(f"✅ Logs sent successfully for task {task_id}")
            return True
        else:
            logger.error(f"❌ Failed to send logs for task {task_id}: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logger.error(f"💥 Exception sending logs for task {task_id}: {e}", exc_info=True) # Add exc_info
        return False

# --- update_task function with minor adjustments ---
def update_task(task: dict, image_paths: list = [], log_message_summary: str = ""):
    """Update task với logs chi tiết và gửi message lên server"""
    server_url = config_loader.get_config_value("app.server_url", "http://localhost:8000")
    client_name = config_loader.get_config_value('app.client_name', 'default_client_name')
    update_url = f"{server_url}/{client_name}/update-task/"
    task_id = task.get("id", "unknown")

    # Ensure message includes the summary log
    original_message = task.get("message", "")
    final_message = f"{original_message} | Summary: {log_message_summary}".strip(" | ")

    logger.info(f"📤 Updating task {task_id} with status: {task.get('status')}, Message: {final_message}")

    data = {
        "id": task_id,
        "status": task.get("status"),
        "message": final_message # Use the combined message
    }

    # Handle files
    files = []
    file_handles = [] # Keep track of opened file handles for safe closing
    try:
        for i, img_path in enumerate(image_paths):
            if os.path.isfile(img_path):
                file_size = os.path.getsize(img_path)
                logger.info(f"📎 Attaching file {i+1}/{len(image_paths)}: {os.path.basename(img_path)} ({file_size:,} bytes)")
                file_handle = open(img_path, "rb")
                file_handles.append(file_handle) # Keep track
                files.append(("images", (os.path.basename(img_path), file_handle, "image/webp")))
            else:
                logger.warning(f"❌ File not found: {img_path}")

        logger.info(f"📡 Sending update request for task {task_id}...")
        response = requests.patch(update_url, data=data, files=files, timeout=30)

        if response.status_code == 200:
            logger.info(f"✅ Task {task_id} updated successfully")
            return response.json()
        else:
            logger.error(f"❌ Failed to update task {task_id}: {response.status_code}")
            logger.error(f"📋 Response: {response.text}")
            return None

    except requests.exceptions.Timeout:
        logger.error(f"⏰ Timeout updating task {task_id}")
    except Exception as e:
        logger.error(f"💥 Exception updating task {task_id}: {e}", exc_info=True) # Add exc_info
    finally:
        # Đảm bảo đóng files trong trường hợp lỗi
        for fh in file_handles:
            try:
                fh.close()
            except Exception as close_error:
                logger.warning(f"⚠️ Error closing file handle: {close_error}")

    return None

# --- worker_loop with improved logging capture ---
def worker_loop():
    """Main worker loop với logging cải thiện"""
    logger.info("🚀 Worker started - Ready to process tasks")
    consecutive_failures = 0
    max_consecutive_failures = 10

    while True:
        task_log_summary = "" # To capture key messages for the task's final update
        try:
            # Reset failure counter khi có task
            task = get_task()
            if not task:
                logger.info("😴 No tasks available, sleeping...")
                time.sleep(5)
                continue

            consecutive_failures = 0  # Reset khi có task
            status = task.get("status", "pending")
            task_id = task.get("id", "unknown")
            task_log_summary = f"Processing task {task_id}" # Initialize summary
            logger.info(f"🎯 Processing task {task_id} with status: {status}")

            if status == "pending":
                new_task = Base_task.from_dict(task)
                start_time = time.time()
                try:
                    logger.info(f"⚡ Starting processing for task {task_id}")
                    # Gọi process_task, nhận cả kết quả và logs (assuming process_task handles its own logging)
                    final_images, log_data = process_task(new_task)
                    if isinstance(final_images, str):
                        final_images = [final_images]

                    processing_time = time.time() - start_time
                    task["status"] = "completed"
                    task["updated_at"] = datetime.utcnow().isoformat() + 'Z' # ISO 8601 UTC
                    success_msg = f"Completed successfully in {processing_time:.2f}s"
                    task["message"] = success_msg
                    task_log_summary += f" - {success_msg}" # Update summary
                    logger.info(f"🎉 Task {task_id} completed successfully")
                    logger.info(f"📊 Generated {len(final_images)} images in {processing_time:.2f}s")

                except Exception as e:
                    processing_time = time.time() - start_time
                    error_msg = str(e)
                    task["status"] = "failed"
                    fail_msg = f"Failed after {processing_time:.2f}s: {error_msg}"
                    task["message"] = fail_msg
                    task_log_summary += f" - {fail_msg}" # Update summary
                    logger.error(f"💥 Error processing task {task_id}: {error_msg}", exc_info=True) # Add exc_info

                    # Optional: Create log_data for failed tasks if needed separately
                    # log_data is handled by process_task, but if you need specific worker-level logs:
                    # log_data = { ... } # As before, or capture worker logs if process_task doesn't

                    final_images = []

            else:
                skip_msg = f"Task {task_id} has status {status}, skipping processing"
                logger.info(f"⏭️ {skip_msg}")
                task_log_summary += f" - {skip_msg}" # Update summary
                # log_data = None # process_task likely handles this
                final_images = []

            # Log kết quả trước khi gửi
            if final_images:
                logger.info(f"📤 Uploading {len(final_images)} images for task {task_id}")
                for i, img_path in enumerate(final_images, 1):
                    if os.path.exists(img_path):
                        size = os.path.getsize(img_path)
                        logger.info(f"  📎 {i}. {os.path.basename(img_path)} ({size:,} bytes)")

            # Update task với message summary
            check = update_task(task, final_images, log_message_summary=task_log_summary)
            if check:
                logger.info(f"✅ Task {task_id} updated successfully with status: {task['status']}")
            else:
                logger.error(f"❌ Failed to update task {task_id}")
                consecutive_failures += 1
                if consecutive_failures >= max_consecutive_failures:
                    logger.critical(f"💥 Too many consecutive failures ({consecutive_failures}), stopping worker")
                    break

        except KeyboardInterrupt:
            logger.info("⏹️ Worker stopped by user (Ctrl+C)")
            break
        except Exception as e:
            consecutive_failures += 1
            logger.critical(f"💥 Unexpected error in worker loop: {e}", exc_info=True) # Add exc_info
            if consecutive_failures >= max_consecutive_failures:
                logger.critical(f"💥 Too many consecutive failures ({consecutive_failures}), stopping worker")
                break

        # Sleep giữa các task
        logger.info("⏸️ Waiting 5 seconds before next task...")
        time.sleep(5)

    logger.info("🛑 Worker stopped")

# --- health_check function remains largely the same ---
def health_check():
    """Kiểm tra sức khỏe của worker và các dependencies"""
    logger.info("🏥 Starting health check...")
    issues = []

    # Kiểm tra config
    try:
        server_url = config_loader.get_config_value("app.server_url", None)
        if not server_url:
            issues.append("❌ Server URL not configured")
        else:
            logger.info(f"✅ Server URL: {server_url}")
    except Exception as e:
        issues.append(f"❌ Config error: {e}")

    # Kiểm tra thư mục
    try:
        mockup_folder = config_loader.get_config_value("app.mockup_folder", "")
        if not os.path.exists(mockup_folder):
            issues.append(f"❌ Mockup folder not found: {mockup_folder}")
        else:
            logger.info(f"✅ Mockup folder exists: {mockup_folder}")

        output_folder = config_loader.get_config_value("app.output_folder", "")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder, exist_ok=True)
            logger.info(f"✅ Created output folder: {output_folder}")
        else:
            logger.info(f"✅ Output folder exists: {output_folder}")
    except Exception as e:
        issues.append(f"❌ Folder check error: {e}")

    # Kiểm tra kết nối server
    try:
        server_url = config_loader.get_config_value("app.server_url", "")
        if server_url:
            response = requests.get(f"{server_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Server connection OK")
            else:
                issues.append(f"❌ Server health check failed: {response.status_code}")
    except Exception as e:
        issues.append(f"❌ Server connection error: {e}")

    # Kiểm tra Photoshop
    try:
        with PhotoshopAutomation(logger) as ps:
            logger.info("✅ Photoshop connection OK")
    except Exception as e:
        issues.append(f"❌ Photoshop connection error: {e}")

    if issues:
        logger.error("🚨 Health check found issues:")
        for issue in issues:
            logger.error(f"  {issue}")
        return False
    else:
        logger.info("✅ Health check passed - All systems OK")
        return True

if __name__ == "__main__":
    try:
        logger.info("🚀 Starting worker loop (health check skipped)...")
        worker_loop()
    except Exception as e:
        logger.critical(f"💥 Failed to start worker: {e}", exc_info=True)
    finally:
        logger.info("🧹 Worker process finished.")
