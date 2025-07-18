import re 
from datetime import timedelta
import re
from datetime import timedelta

def parse_time_delta(period_str: str) -> timedelta:
    """
    Parse chuỗi kiểu '1d', '2w', '3m', '1w2d3h', '2m5d', ... thành timedelta.
    Hỗ trợ: s (giây), min (phút), h (giờ), d (ngày), w (tuần), m (tháng, 30 ngày), y (năm, 365 ngày)
    """
    if not period_str or not isinstance(period_str, str):
        raise ValueError("Input phải là chuỗi (vd: '1d', '2w', '1w2d3h', '2m5d', ...)")

    # Regex tìm tất cả cặp số-đơn vị, ví dụ: '2d', '1w', '3h', '5min', '1y'
    # Đơn vị: s, min, h, d, w, m, y (không phân biệt hoa/thường)
    regex = re.compile(r"(\d+)(s|min|h|d|w|m|y)", re.IGNORECASE)
    matches = regex.findall(period_str.replace(" ", ""))  # Bỏ toàn bộ khoảng trắng để ghép chuỗi liền

    if not matches:
        raise ValueError("Sai định dạng. Ví dụ hợp lệ: '1d', '2w', '1w2d3h', '2m5d', ...")

    total_seconds = 0
    for value, unit in matches:
        n = int(value)
        unit = unit.lower()
        if unit == 's':
            total_seconds += n
        elif unit == 'min':
            total_seconds += n * 60
        elif unit == 'h':
            total_seconds += n * 3600
        elif unit == 'd':
            total_seconds += n * 86400
        elif unit == 'w':
            total_seconds += n * 7 * 86400
        elif unit == 'm':
            total_seconds += n * 30 * 86400  # tháng tính gần đúng 30 ngày
        elif unit == 'y':
            total_seconds += n * 365 * 86400
        else:
            raise ValueError(f"Đơn vị thời gian không hỗ trợ: {unit}")

    return timedelta(seconds=total_seconds)
