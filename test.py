from PIL import Image


# Hỗ trợ Resampling cho Pillow mới/cũ
try:
    LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    LANCZOS = Image.LANCZOS
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

if __name__ == "__main__":
    input_path = r'D:\dev\sple\make-mockup-client\statics\output\test\test-best-selling.png'  # Thay bằng đường dẫn ảnh đầu vào
    output_path = r'D:\dev\sple\make-mockup-client\statics\output\test\output.webp'  # Đường dẫn lưu ảnh đầu ra
    convert_image_with_alpha(input_path, output_path)