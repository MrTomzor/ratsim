#!/usr/bin/env python3
import sys
from PIL import Image

def main():
    if len(sys.argv) != 5:
        print("Usage: python resize_mpp.py <input_image> <output_image> <image_width_meters> <desired_meters_per_pixel>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    image_width_m = float(sys.argv[3])
    desired_mpp = float(sys.argv[4])

    # Load image
    img = Image.open(input_path).convert("RGB")
    width_px, height_px = img.size

    # Compute current meters per pixel
    current_mpp = image_width_m / width_px

    # Compute new width and height in pixels for the desired resolution
    new_width_px = int(round(image_width_m / desired_mpp))
    scale_factor = new_width_px / width_px
    new_height_px = int(round(height_px * scale_factor))

    # Resample the image
    resized_img = img.resize((new_width_px, new_height_px), resample=Image.Resampling.BILINEAR)

    # Save the output
    resized_img.save(output_path)
    print(f"Resized image saved to {output_path}")
    print(f"Original size: {width_px}x{height_px}px  ({current_mpp:.4f} m/px)")
    print(f"New size:      {new_width_px}x{new_height_px}px  ({desired_mpp:.4f} m/px)")

if __name__ == "__main__":
    main()
