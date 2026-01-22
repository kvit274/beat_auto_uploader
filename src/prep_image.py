from PIL import Image
import os

def fit_thumbnail(in_path, out_path, w=1920, h=1080):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img = Image.open(in_path).convert("RGB")
    img.thumbnail((w, h))
    canvas = Image.new("RGB", (w, h), (0,0,0))
    x, y = (w - img.width)//2, (h - img.height)//2
    canvas.paste(img, (x,y))
    canvas.save(out_path, quality=95)
    return out_path
