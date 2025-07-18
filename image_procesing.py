
from models.task import Base_task
from utils.task_utils import read_tasks, write_tasks
from utils.load_config import ConfigLoader
from utils.response_util import create_slug
from typing import Dict, Any, Optional
import os 
from lib.photoshop_automation import PhotoshopAutomation
import time
import logging
import re
from utils.path_utils import normalize_path
from PIL import Image
import os
import io

logger = logging.getLogger(__name__)
LABELS = [
    "best-selling",
    "fashion-forward",
    "high-quality",
    "latest-model",
    "new-arrival",
    "premium-grade",
    "top-rated",
    "trendy"
]
try:
    LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    LANCZOS = Image.LANCZOS

def process_task(task: Base_task) -> list:
    max_retries = 3
    retry_delay = 5  # giây
    output_images = []

    for attempt in range(max_retries):
        try:
            logger.info(f"🔁 Attempt {attempt+1} to process task {task.id}")
            with PhotoshopAutomation(logger) as photoshop:
                mockup_folder = ConfigLoader().get_config_value("app.mockup_folder", "")
                mockup_folder = os.path.join(mockup_folder, f"{task.store_name}-{task.product_type}")
                current_path = os.path.dirname(os.path.abspath(__file__))
                psd_file = [f for f in os.listdir(mockup_folder) if f.endswith(".psd")]
                if not psd_file:
                    raise FileNotFoundError("No PSD files found in the mockup folder.")
                
                for psd in psd_file:
                    psd_path = normalize_path(os.path.join(mockup_folder, psd))
                    slug_name = create_slug(task.product_name)
                    image_name = generate_image_filename(psd, slug_name, LABELS)
                    image_files = normalize_path(os.path.join(current_path, task.downloaded_image_path))
                    export_folder = normalize_path(os.path.join(ConfigLoader().get_config_value("app.output_folder", ""), slug_name))
                    os.makedirs(export_folder, exist_ok=True)

                    res = photoshop.make_mockup_image(
                        psd_file=psd_path,
                        image_files=[image_files],
                        export_folder=export_folder,
                        output_names=[image_name]
                    )
                    output_images.extend(res)
                
                break  # ✔ Thành công, thoát retry loop

        except Exception as e:
            logger.error(f"❌ Error processing task {task.id}: {e}")
            if attempt < max_retries - 1:
                logger.warning(f"⏳ Retrying after {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                logger.error("💥 Max retries reached. Giving up.")
                return []

    # Chuyển ảnh sang webp và nén
    for i, output_image in enumerate(output_images):
        output_image = normalize_path(output_image)
        if not output_image.endswith(".webp"):
            webp_output = os.path.splitext(output_image)[0] + ".webp"
            logger.info(f"Converting {output_image} to {webp_output} and compressing...")
            convert_to_webp_and_compress(output_image, webp_output)
            output_images[i] = webp_output
        else:
            output_images[i] = output_image

    return output_images

def get_index_from_filename(mockup_filename: str) -> int:
    """
    Tìm số thứ tự (1-2-3...) trong tên file mockup, ví dụ JacketWow-MK-3.psd -> 3
    """
    match = re.search(r'-MK-(\d+)', mockup_filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None

def generate_image_filename(mockup_filename: str, image_filename: str, labels: list, default_label: str = "main") -> str:
    """
    Sinh tên file ảnh mới dựa vào tên mockup, tên file ảnh và danh sách label.
    """
    idx = get_index_from_filename(mockup_filename)
    if idx is not None and 1 <= idx <= len(labels):
        label = labels[idx-1]
    else:
        label = default_label
    slug = label
    return f"{image_filename}-{slug}"


def convert_image_with_alpha(input_path, output_path, resize_to=(1024, 1024), quality=85):
    try:
        img = Image.open(input_path).convert("RGBA")

        # Resize giữ tỷ lệ
        img.thumbnail(resize_to, LANCZOS)

        # Tạo nền trong suốt
        background = Image.new("RGBA", resize_to, (255, 255, 255, 0))

        # Tính vị trí căn giữa
        offset = ((resize_to[0] - img.width) // 2, (resize_to[1] - img.height) // 2)

        # Lấy alpha mask
        alpha = img.split()[3]  # Kênh A

        # Paste dùng mask để giữ trong suốt
        background.paste(img, offset, mask=alpha)

        # Lưu ảnh webp có alpha, nén nhẹ để tránh lỗi viền
        background.save(output_path, format="WEBP", quality=quality, method=6, lossless=False)

        print(f"✅ Done: {output_path}")

    except Exception as e:
        print("❌ Error:", e)
