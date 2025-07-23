# image_procesing.py (Corrected spelling from 'image_processing')
from models.task import Base_task
from utils.task_utils import read_tasks, write_tasks
from utils.load_config import ConfigLoader
from utils.response_util import create_slug
from utils.enhanced_logger_manager import get_task_logger, enhanced_logger_manager
from typing import Dict, Any, Optional, Tuple, List
import os
import logging
import re
from utils.path_utils import normalize_path
from PIL import Image
import time
import traceback
from lib.photoshop_automation import PhotoshopAutomation

# Main logger for this module (if needed for setup issues, though task_logger is preferred)
module_logger = logging.getLogger(__name__)

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

def process_task(task: Base_task) -> Tuple[List[str], Dict[str, Any]]:
    """
    Process task và trả về kết quả cùng với logs.
    Args:
        task (Base_task): The task object to process.
    Returns:
        Tuple[list, Dict[str, Any]]: A tuple containing (output_images_paths, log_data_dict).
                                     output_images_paths is a list of paths to the generated images.
                                     log_data_dict contains detailed logs for the task.
    Raises:
        Exception: If processing fails after all retries.
    """
    task_id = str(task.id)
    # Obtain the dedicated logger for this specific task
    task_logger = get_task_logger(task_id)
    max_retries = 3
    retry_delay = 5  # seconds
    output_images: List[str] = [] # Explicitly type the list

    task_logger.info("=" * 40)
    task_logger.info(f"🚀 Initiating task processing | Task ID: {task_id}")
    task_logger.info(f"📋 Task Details | Store: '{task.store}', Product: '{task.product_name}', Type: '{task.product_type}'")
    start_time = time.time()

    for attempt in range(1, max_retries + 1): # Start from 1 for clarity
        task_logger.info("-" * 30)
        task_logger.info(f"🔁 Processing Attempt #{attempt}/{max_retries} for task {task_id}")

        try:
            # --- Setup and Configuration ---
            mockup_folder_base = ConfigLoader().get_config_value("app.mockup_folder", "")
            mockup_folder = os.path.join(mockup_folder_base, f"{task.store}-{task.product_type}")
            current_path = os.path.dirname(os.path.abspath(__file__))

            task_logger.debug(f"📁 Configured mockup base folder: {mockup_folder_base}")
            task_logger.info(f"📁 Resolved mockup folder path: {mockup_folder}")
            task_logger.debug(f"📍 Current script directory: {current_path}")

            # --- Validation ---
            if not os.path.exists(mockup_folder):
                error_msg = f"📁 Mockup folder not found: {mockup_folder}"
                task_logger.error(f"❌ Setup Error | {error_msg}")
                raise FileNotFoundError(error_msg)

            psd_files = [f for f in os.listdir(mockup_folder) if f.lower().endswith(".psd")]
            if not psd_files:
                warning_msg = f"📭 No PSD files found in mockup folder: {mockup_folder}"
                task_logger.warning(f"⚠️ Validation Warning | {warning_msg}")
                 # Consider if this should raise an error or just return empty results
                 # For now, let it proceed, it might log a warning later if no images are generated.

            task_logger.info(f"📄 PSD Files Found | Count: {len(psd_files)}, Files: {psd_files}")

            # --- Photoshop Processing Loop ---
            with PhotoshopAutomation(task_logger) as photoshop:
                task_logger.info("🎨 Establishing connection with Photoshop application...")
                # Assuming PhotoshopAutomation logs its own connection status internally

                processed_psd_count = 0
                for i, psd_filename in enumerate(psd_files, 1):
                    task_logger.info(f"🔧 PSD Processing | File {i}/{len(psd_files)}: '{psd_filename}'")
                    psd_path = normalize_path(os.path.join(mockup_folder, psd_filename))
                    slug_name = create_slug(task.product_name)
                    image_name = generate_image_filename(psd_filename, slug_name, LABELS)
                    # Ensure task.downloaded_image_path is absolute or relative to the correct base
                    image_files_input = normalize_path(os.path.join(current_path, task.downloaded_image_path))
                    export_folder = normalize_path(os.path.join(ConfigLoader().get_config_value("app.output_folder", ""), slug_name))

                    task_logger.debug(f"   📥 Input Image Path: {image_files_input}")
                    task_logger.debug(f"   📤 Export Destination: {export_folder}")
                    task_logger.debug(f"   🏷️ Generated Output Name: {image_name}")

                    # Validate input image
                    if not os.path.exists(image_files_input):
                        error_msg = f"❌ Input image file not found: {image_files_input}"
                        task_logger.error(f"   ❌ PSD Error | {error_msg}")
                        # Continue to next PSD file instead of failing the whole task
                        continue

                    # Ensure export folder exists
                    os.makedirs(export_folder, exist_ok=True)
                    task_logger.debug(f"   ✅ Verified export folder exists: {export_folder}")

                    # Execute Photoshop action
                    task_logger.info(f"   🎨 Executing Photoshop Automation for '{psd_filename}'...")
                    try:
                        # Assuming make_mockup_image returns a list of generated file paths
                        generated_image_paths = photoshop.make_mockup_image(
                            psd_file=psd_path,
                            image_files=[image_files_input], # Ensure list format if required
                            export_folder=export_folder,
                            output_names=[image_name]
                        )
                        processed_psd_count += 1

                        if generated_image_paths:
                            count_generated = len(generated_image_paths)
                            task_logger.info(f"   ✅ PSD Success | Generated {count_generated} image(s)")
                            task_logger.debug(f"      📋 Generated Files: {generated_image_paths}")
                            output_images.extend(generated_image_paths)
                        else:
                            warning_msg = f"No images were generated by Photoshop for PSD '{psd_filename}'."
                            task_logger.warning(f"   ⚠️ PSD Warning | {warning_msg}")

                    except Exception as psd_error:
                        # Log error specific to this PSD processing step
                        task_logger.error(f"   💥 PSD Processing Failed | PSD: '{psd_filename}', Error: {psd_error}", exc_info=True)

                # --- Post PSD Processing Check ---
                if processed_psd_count == 0 and psd_files:
                     # Only error if there were PSD files but none were processed successfully
                     task_logger.error(f"💥 Critical Error | No PSD files were processed successfully out of {len(psd_files)} found.")
                     raise Exception("All PSD processing attempts failed.")

            # If we reach here, the main processing logic succeeded
            task_logger.info(f"✅ Core Processing Completed | Attempt #{attempt} successful")
            break # Exit retry loop on success

        except Exception as e:
            error_msg = str(e)
            # Log the full traceback for debugging within the task log
            task_logger.error(f"❌ Attempt #{attempt} Failed | Error: {error_msg}", exc_info=True)
            if attempt < max_retries:
                task_logger.warning(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                task_logger.error(f"💥 All {max_retries} attempts failed. Aborting task {task_id}.")
                # Prepare log data indicating failure
                processing_time = time.time() - start_time
                log_data_failure = {
                    'task_id': task_id,
                    'processing_time': processing_time,
                    'status': 'failed',
                    'error': error_msg,
                    'logs': enhanced_logger_manager.get_task_logs(task_id),
                    'log_string': enhanced_logger_manager.get_task_logs_string(task_id)
                }
                # Ensure cleanup happens even on final failure
                enhanced_logger_manager.cleanup_task_logger(task_id)
                raise Exception(f"Max retries reached for task {task_id}. Final error: {error_msg}") from e

    # --- Image Conversion (WebP) ---
    task_logger.info("-" * 30)
    task_logger.info("🔄 Starting Image Conversion to WebP format...")
    converted_images: List[str] = []
    conversion_success_count = 0
    conversion_skip_count = 0
    conversion_error_count = 0

    for i, original_image_path in enumerate(output_images, 1):
        original_image_path = normalize_path(original_image_path) # Normalize again for safety
        filename = os.path.basename(original_image_path)
        task_logger.info(f"🖼️ Converting Image {i}/{len(output_images)}: '{filename}'")

        if original_image_path.lower().endswith(".webp"):
            task_logger.info(f"   ✅ Already WebP | Skipping conversion for '{filename}'")
            converted_images.append(original_image_path)
            conversion_skip_count += 1
            continue

        # Determine WebP output path
        webp_output_path = os.path.splitext(original_image_path)[0] + ".webp"
        task_logger.debug(f"   🔄 Target WebP Path: {webp_output_path}")

        try:
            task_logger.info(f"   🔄 Initiating Conversion | '{filename}' -> '{os.path.basename(webp_output_path)}'")
            convert_image_with_alpha(original_image_path, webp_output_path, task_logger=task_logger)
            converted_images.append(webp_output_path)
            conversion_success_count += 1

            # Remove original file after successful conversion
            if os.path.exists(original_image_path) and original_image_path != webp_output_path:
                os.remove(original_image_path)
                task_logger.debug(f"   🗑️ Deleted Original File: '{filename}'")

        except Exception as conversion_error:
             conversion_error_count += 1
             error_msg = f"Failed to convert '{filename}': {conversion_error}"
             task_logger.error(f"   ❌ Conversion Error | {error_msg}", exc_info=True)
             # Keep the original file if conversion fails
             converted_images.append(original_image_path)


    # --- Finalization ---
    processing_time = time.time() - start_time
    task_logger.info("=" * 40)
    task_logger.info(f"🏁 Task Processing Completed | Task ID: {task_id}")
    task_logger.info(f"📊 Summary | "
                     f"Total Time: {processing_time:.2f}s, "
                     f"PSDs Processed: {len(psd_files)}, "
                     f"Images Converted: {conversion_success_count}, "
                     f"Images Skipped (Already WebP): {conversion_skip_count}, "
                     f"Conversion Errors: {conversion_error_count}, "
                     f"Final Images: {len(converted_images)}")

    # Prepare final successful log data
    log_data_success = {
        'task_id': task_id,
        'processing_time': processing_time,
        'status': 'completed',
        'images_generated': len(converted_images),
        'logs': enhanced_logger_manager.get_task_logs(task_id),
        'log_string': enhanced_logger_manager.get_task_logs_string(task_id),
        'details': {
            'psd_files_found': len(psd_files),
            'psd_files_processed': len([f for f in psd_files if f]), # Placeholder logic, refine if needed
            'conversion': {
                'successful': conversion_success_count,
                'skipped': conversion_skip_count,
                'errors': conversion_error_count
            }
        }
    }

    # Cleanup the dedicated logger for this task
    enhanced_logger_manager.cleanup_task_logger(task_id)
    task_logger.info(f"🧹 Cleaned up task-specific logger for ID: {task_id}")

    return converted_images, log_data_success

# --- Helper Functions (Logging improvements minor) ---

def get_index_from_filename(mockup_filename: str) -> Optional[int]:
    """
    Tìm số thứ tự (1-2-3...) trong tên file mockup, ví dụ JacketWow-MK-3.psd -> 3
    """
    match = re.search(r'-MK-(\d+)', mockup_filename, re.IGNORECASE)
    if match:
        index = int(match.group(1))
        # module_logger.debug(f"Extracted index {index} from filename '{mockup_filename}'")
        return index
    # module_logger.debug(f"No index found in filename '{mockup_filename}'")
    return None

def generate_image_filename(mockup_filename: str, image_filename: str, labels: list, default_label: str = "main") -> str:
    """
    Sinh tên file ảnh mới dựa vào tên mockup, tên file ảnh và danh sách label.
    """
    idx = get_index_from_filename(mockup_filename)
    if idx is not None and 1 <= idx <= len(labels):
        label = labels[idx-1]
        # module_logger.debug(f"Label '{label}' selected for index {idx} from filename '{mockup_filename}'")
    else:
        label = default_label
        # module_logger.debug(f"Default label '{default_label}' used for filename '{mockup_filename}' (index: {idx})")
    slug = label
    generated_name = f"{image_filename}-{slug}"
    # module_logger.debug(f"Generated filename: '{generated_name}' from mockup '{mockup_filename}', base '{image_filename}'")
    return generated_name

def convert_image_with_alpha(input_path: str, output_path: str, resize_to: Tuple[int, int] = (1024, 1024), quality: int = 85, task_logger: Optional[logging.Logger] = None):
    """
    Convert image to WebP với alpha channel và logging chi tiết.
    Args:
        input_path (str): Đường dẫn tới ảnh đầu vào.
        output_path (str): Đường dẫn lưu ảnh WebP đầu ra.
        resize_to (Tuple[int, int]): Kích thước mục tiêu (width, height). Mặc định (1024, 1024).
        quality (int): Chất lượng WebP (0-100). Mặc định 85.
        task_logger (Optional[logging.Logger]): Logger cụ thể cho task. Nếu None, dùng logger module.
    Raises:
        Exception: Nếu có lỗi trong quá trình mở, xử lý hoặc lưu ảnh.
    """
    if task_logger is None:
        task_logger = module_logger # Fallback to module logger if task logger not provided

    input_filename = os.path.basename(input_path)
    output_filename = os.path.basename(output_path)
    task_logger.info(f"🔄 WebP Conversion | '{input_filename}' -> '{output_filename}'")
    task_logger.debug(f"   📏 Resize Target: {resize_to[0]}x{resize_to[1]}px, Quality: {quality}")

    try:
        task_logger.debug(f"   🖼️ Opening source image: '{input_filename}'")
        img = Image.open(input_path).convert("RGBA")
        original_width, original_height = img.size
        task_logger.debug(f"   📐 Original Dimensions: {original_width}x{original_height}px")

        # Resize image maintaining aspect ratio
        img.thumbnail(resize_to, LANCZOS)
        resized_width, resized_height = img.size
        task_logger.debug(f"   📐 Resized Dimensions: {resized_width}x{resized_height}px")

        # Create a transparent background canvas
        background = Image.new("RGBA", resize_to, (255, 255, 255, 0))
        task_logger.debug(f"   🎨 Created transparent canvas: {resize_to[0]}x{resize_to[1]}px")

        # Calculate centered offset
        offset_x = (resize_to[0] - resized_width) // 2
        offset_y = (resize_to[1] - resized_height) // 2
        offset = (offset_x, offset_y)
        task_logger.debug(f"   📍 Calculated centering offset: ({offset_x}, {offset_y})")

        # Extract alpha channel
        alpha_channel = img.split()[3] # Channel A
        task_logger.debug("   🔍 Extracted alpha channel")

        # Paste resized image onto background using alpha as mask
        task_logger.debug("   🧻 Pasting resized image onto background with alpha mask")
        background.paste(img, offset, mask=alpha_channel)

        # Save as WebP with alpha
        task_logger.debug(f"   💾 Saving WebP image to '{output_filename}' with quality={quality}")
        # Using method=6 and lossless=False for better compression, adjust if needed
        background.save(output_path, format="WEBP", quality=quality, method=6, lossless=False)
        task_logger.debug("   💾 WebP save command executed")

        # Verify output and log file size
        if os.path.exists(output_path):
            file_size_bytes = os.path.getsize(output_path)
            file_size_kb = file_size_bytes / 1024
            task_logger.info(f"   ✅ Conversion Successful | '{output_filename}' ({file_size_kb:.2f} KB)")
        else:
             # This is a critical error if the file wasn't created
             raise FileNotFoundError(f"WebP file was not created at expected path: {output_path}")

    except FileNotFoundError as fnf_error:
        task_logger.error(f"   ❌ File Not Found Error | {fnf_error}")
        raise # Re-raise as it's a critical setup issue
    except Exception as e:
        error_msg = f"Error during conversion of '{input_filename}': {e}"
        task_logger.error(f"   💥 Conversion Failed | {error_msg}", exc_info=True) # Include traceback
        raise Exception(error_msg) from e # Wrap and re-raise
