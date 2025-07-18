import os
from pathlib import Path
from urllib.parse import unquote

def normalize_path(path_str, unquote_url=False, resolve_absolute=True):
    """
    Chuẩn hóa đường dẫn:
    - Thay \ hoặc / thành đúng ký tự phân cách OS
    - Loại bỏ ký tự thừa
    - Option: Unquote url (giải mã %20 thành khoảng trắng)
    - Option: resolve_absolute: chuyển thành đường dẫn tuyệt đối

    :param path_str: Đường dẫn input (str)
    :param unquote_url: True nếu muốn chuyển %20 thành khoảng trắng
    :param resolve_absolute: True nếu muốn chuyển thành đường dẫn tuyệt đối
    :return: str (chuẩn hóa)
    """
    if unquote_url:
        path_str = unquote(path_str)
    # Đưa về Path object để OS tự xử lý dấu phân cách
    path_obj = Path(path_str)
    if resolve_absolute:
        try:
            # Sửa lỗi nếu file không tồn tại mà vẫn muốn lấy absolute
            path_obj = path_obj.resolve(strict=False)
        except Exception:
            path_obj = path_obj.absolute()
    return str(path_obj)

# Ví dụ sử dụng:
if __name__ == "__main__":
    input_path = r"D:\dev\sple\make-mockup-client/downloads\1234_1ed8c774-9e3b-4edd-9827-a81d5cd54780_Detroit%20Tigers_20250616_153513.png"
    normalized = normalize_path(input_path)
    print("Normalized:", normalized)
