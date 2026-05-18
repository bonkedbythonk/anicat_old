import os
from PIL import Image

def fix_icon_source(input_path, output_path):
    print(f"Loading image from {input_path}...")
    img = Image.open(input_path).convert("RGBA")
    width, height = img.size
    pixels = img.load()
    assert pixels is not None
    
    # We will flood-fill from the four corners to find the white background area
    corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
    bg_pixels = set()
    
    for start_x, start_y in corners:
        if (start_x, start_y) in bg_pixels:
            continue
            
        r, g, b, a = pixels[start_x, start_y]  # type: ignore
        if (r + g + b) / 3.0 < 200:
            print(f"Skipping corner {start_x}, {start_y} because it is not white: {(r, g, b)}")
            continue
            
        queue = [(start_x, start_y)]
        bg_pixels.add((start_x, start_y))
        
        while queue:
            cx, cy = queue.pop(0)
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in bg_pixels:
                    nr, ng, nb, na = pixels[nx, ny]  # type: ignore
                    # If it is white or very bright (RGB average > 240)
                    if (nr + ng + nb) / 3.0 > 240:
                        bg_pixels.add((nx, ny))
                        queue.append((nx, ny))
                        
    print(f"Found {len(bg_pixels)} white background pixels out of {width * height} total pixels.")
    
    # Create the new image with transparency
    new_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    new_pixels = new_img.load()
    assert new_pixels is not None
    
    # Copy all pixels, but make bg_pixels transparent
    for y in range(height):
        for x in range(width):
            if (x, y) in bg_pixels:
                new_pixels[x, y] = (0, 0, 0, 0)
            else:
                # Keep original pixel, ensure it has alpha=255
                r, g, b, a = pixels[x, y]  # type: ignore
                new_pixels[x, y] = (r, g, b, 255)
                
    # Save the processed image
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    new_img.save(output_path, "PNG")
    print(f"Successfully saved transparent icon source to {output_path}!")

if __name__ == "__main__":
    fix_icon_source(
        "web/src-tauri/icons/icon_source_real.png",
        "web/src-tauri/icons/icon_source.png"
    )
