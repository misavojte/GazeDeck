#!/usr/bin/env python3

import sys
from pupil_labs.real_time_screen_gaze import marker_generator
import cv2
import numpy as np

def save_apriltag(marker_id, output_path="apriltags", size=100):
    """Generate and save a single AprilTag as PNG using pupil_labs marker generator."""
    try:
        # Generate the marker using pupil_labs (this creates valid AprilTags)
        marker_pixels = marker_generator.generate_marker(marker_id=marker_id)

        # Convert to numpy array and ensure proper format
        marker_array = np.array(marker_pixels, dtype=np.uint8)

        # Ensure it's 2D
        if marker_array.ndim == 1:
            side_length = int(np.sqrt(marker_array.size))
            marker_array = marker_array.reshape(side_length, side_length)

        # Scale to desired size using nearest neighbor to preserve pattern
        scaled_marker = cv2.resize(marker_array, (size, size), interpolation=cv2.INTER_NEAREST)

        # Save using OpenCV
        import os
        os.makedirs(output_path, exist_ok=True)

        filename = f"{output_path}/apriltag_{marker_id}.png"
        cv2.imwrite(filename, scaled_marker)
        print(f"Saved AprilTag {marker_id} to {filename}")

        # Verify the saved image
        verify_img = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
        if verify_img is not None:
            print(f"Verification: saved image shape {verify_img.shape}, unique values: {np.unique(verify_img)}")
        else:
            print("Warning: Could not verify saved image")

        return True

    except Exception as e:
        print(f"Error generating AprilTag {marker_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Generate multiple AprilTags and save them as PNG files."""
    if len(sys.argv) > 1:
        # Use command line arguments
        start_id = int(sys.argv[1])
        end_id = int(sys.argv[2]) if len(sys.argv) > 2 else start_id + 1
        output_path = sys.argv[3] if len(sys.argv) > 3 else "apriltags"
        size = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    else:
        # Default: generate tags 0-10
        start_id = 0
        end_id = 10
        output_path = "apriltags"
        size = 100

    print(f"Generating AprilTags from ID {start_id} to {end_id-1} ({size}x{size}px)...")

    success_count = 0
    for marker_id in range(start_id, end_id):
        if save_apriltag(marker_id, output_path, size):
            success_count += 1

    print(f"Successfully generated {success_count} AprilTags")

if __name__ == "__main__":
    main()