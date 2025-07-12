import cv2
import base64


def image_to_base64(img_np):
    success, buffer = cv2.imencode(".png", img_np)
    if not success:
        raise ValueError("Gagal meng-encode gambar ke PNG.")
    return base64.b64encode(buffer.tobytes()).decode("utf-8")
