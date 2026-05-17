import os
from PIL import Image

def resize_original_tray():
    img_path = "web/src-tauri/icons/tray-icon.png"
    print(f"Loading original tray icon from {img_path}...")
    img = Image.open(img_path).convert("RGBA")
    
    # Crop to active bounding box of non-transparent pixels
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
        print(f"Cropped to bounding box: {bbox}")
        
    # Resize the cropped cat shape to fit within a 22x22 box (leaving beautiful padding)
    target_size = 22
    w, h = img.size
    if w > h:
        new_w = target_size
        new_h = int(h * (target_size / w))
    else:
        new_h = target_size
        new_w = int(w * (target_size / h))
        
    resized_img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    
    # Create the final 32x32 canvas with transparent background
    canvas_size = 32
    final_canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    
    # Calculate offset to paste it right in the center
    offset_x = (canvas_size - new_w) // 2
    offset_y = (canvas_size - new_h) // 2
    
    final_canvas.paste(resized_img, (offset_x, offset_y), resized_img)
    
    # Save the output
    final_canvas.save(img_path, "PNG")
    print(f"Successfully processed, padded, and saved original tray icon!")

if __name__ == "__main__":
    resize_original_tray()
