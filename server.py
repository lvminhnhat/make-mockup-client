from fastapi import FastAPI , UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
app = FastAPI()
import uuid
import os

# Cho phép truy cập file tĩnh trong thư mục uploads
app.mount("/images", StaticFiles(directory="statics/uploads"), name="images")

@app.get("/get_task/{client_name}")
def get_product(client_name: str):
    # Dữ liệu này có thể lấy từ DB, file hoặc hard-code như ví dụ này
    return {
        "id": "1234",
        "product_name": "test",
        "product_type": "test",
        "store": "test",
        "status": "pending",
        "image_url": f"http://localhost:8000/images/image.png"
    }

@app.post("/update_task")
async def update_task(
    id: str = Form(...),
    status: str = Form(...),
    updated_at: str = Form(...),
    images: Optional[List[UploadFile]] = File(None)
):
    # Xử lý data: id, status, updated_at
    # Xử lý ảnh: images là list UploadFile (nếu có)
    saved_images = []
    if images:
        for img in images:
            filename = f"{uuid.uuid4().hex}_{img.filename}"
            save_path = os.path.join("statics/uploads", filename)
            with open(save_path, "wb") as f:
                f.write(await img.read())
            saved_images.append(save_path)
    return {
        "id": id,
        "status": status,
        "updated_at": updated_at,
        "image_paths": saved_images
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)