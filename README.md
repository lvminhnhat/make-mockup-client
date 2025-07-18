# Photoshop Mockup Client Library

Thư viện Python để tự động hóa Photoshop tạo mockup images từ file PSD và ảnh đầu vào.

## 🚀 Tính năng

- ✅ Tự động thay thế Smart Objects trong file PSD
- ✅ Hỗ trợ xuất PNG, JPG, JPEG
- ✅ Xử lý batch nhiều ảnh cùng lúc
- ✅ Logging chi tiết quá trình xử lý
- ✅ Context manager tự động quản lý Photoshop session
- ✅ Xử lý lỗi và validate đầu vào

## 📋 Yêu cầu

- **Adobe Photoshop** phải được cài đặt và chạy
- **Python 3.7+**
- **Windows** (do photoshop-python-api chỉ hỗ trợ Windows)

## 🔧 Cài đặt

1. Clone hoặc download project này
2. Cài đặt dependencies:
```bash
pip install -r requirements.txt
```

## 📖 Cách sử dụng

### Sử dụng cơ bản

```python
from src.photoshop_mockup_client import PhotoshopMockupClient
from src.export_types import ExportType

# Sử dụng context manager
with PhotoshopMockupClient() as client:
    output_files = client.make_mockup_image(
        psd_file=r"C:\path\to\mockup.psd",
        image_files=[r"C:\path\to\image1.jpg", r"C:\path\to\image2.png"],
        export_folder=r"C:\output",
        export_file_name="my_mockup",
        export_type=ExportType.PNG
    )
    
    print("Created files:", output_files)
```

### Xuất nhiều format

```python
formats = [ExportType.PNG, ExportType.JPG]

with PhotoshopMockupClient() as client:
    for fmt in formats:
        client.make_mockup_image(
            psd_file=psd_file,
            image_files=image_files,
            export_folder=export_folder,
            export_file_name=f"mockup_{fmt.value}",
            export_type=fmt
        )
```

## 📁 Cấu trúc project

```
make-mockup-client/
├── src/
│   ├── __init__.py
│   ├── photoshop_mockup_client.py  # Class chính
│   └── export_types.py             # Enum cho format xuất
├── examples.py                     # Các ví dụ sử dụng
├── requirements.txt                # Dependencies
└── README.md                       # Tài liệu này
```

## 🎯 API Reference

### PhotoshopMockupClient

#### `__init__(log_level=logging.INFO)`
Khởi tạo client với mức độ logging.

#### `make_mockup_image(psd_file, image_files, export_folder, export_file_name, export_type=ExportType.PNG)`

**Parameters:**
- `psd_file` (str): Đường dẫn file PSD mockup
- `image_files` (List[str]): Danh sách đường dẫn ảnh cần chèn
- `export_folder` (str): Thư mục xuất file kết quả
- `export_file_name` (str): Tên file xuất (không có extension)
- `export_type` (ExportType): Format xuất (PNG, JPG, JPEG)

**Returns:**
- `List[str]`: Danh sách đường dẫn các file đã tạo

**Raises:**
- `Exception`: Khi Photoshop session chưa khởi tạo
- `FileNotFoundError`: Khi không tìm thấy file PSD hoặc ảnh
- `PermissionError`: Khi không có quyền ghi thư mục xuất

### ExportType

Enum định nghĩa các format xuất:
- `ExportType.PNG` - Xuất PNG
- `ExportType.JPG` - Xuất JPG  
- `ExportType.JPEG` - Xuất JPEG

## 📝 Ví dụ chi tiết

Xem file `examples.py` để có các ví dụ chi tiết:
- Sử dụng cơ bản
- Xuất nhiều format
- Xử lý batch nhiều ảnh

## ⚠️ Lưu ý quan trọng

1. **Photoshop phải chạy**: Đảm bảo Adobe Photoshop đang mở trước khi chạy script
2. **Smart Objects**: File PSD cần có Smart Objects để thư viện có thể thay thế ảnh
3. **Đường dẫn**: Sử dụng đường dẫn tuyệt đối (absolute path)
4. **Quyền ghi**: Đảm bảo thư mục xuất có quyền ghi

## 🐛 Xử lý lỗi

Thư viện có logging chi tiết để debug:

```python
import logging

# Bật debug logging
with PhotoshopMockupClient(log_level=logging.DEBUG) as client:
    # ... your code
```

## 🔄 Workflow hoạt động

1. Mở file PSD trong Photoshop
2. Với mỗi ảnh đầu vào:
   - Tìm Smart Objects trong PSD
   - Thay thế nội dung Smart Object bằng ảnh
   - Xuất file với format chỉ định
3. Đóng PSD không lưu thay đổi
4. Trả về danh sách file đã tạo

## 🤝 Đóng góp

Nếu bạn muốn đóng góp hoặc báo lỗi, vui lòng tạo issue hoặc pull request.

## 📄 License

MIT License - Xem file LICENSE để biết chi tiết.
