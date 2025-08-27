#!/usr/bin/env python3

import sys
import cv2
from pupil_labs.real_time_screen_gaze import marker_generator
from PIL import Image
import numpy as np

def save_apriltag(marker_id, output_path="apriltags"):
    """Generate and save a single AprilTag as PNG."""
    try:
        # Generate the marker
        marker_pixels = marker_generator.generate_marker(marker_id=marker_id)

        # Debug info (uncomment if needed)
        # print(f"Marker {marker_id} - Shape: {marker_pixels.shape}, dtype: {marker_pixels.dtype}")
        # print(f"Pattern preview:\n{marker_pixels}")

        # Convert to numpy array if needed
        marker_array = np.array(marker_pixels)

        # Handle different data formats
        if marker_array.dtype == bool:
            # Boolean array (0/1) - convert to uint8
            marker_array = marker_array.astype(np.uint8) * 255
        elif marker_array.dtype in [np.float32, np.float64]:
            # Float array (0.0-1.0) - convert to uint8
            marker_array = (marker_array * 255).astype(np.uint8)
        elif marker_array.dtype == np.uint8:
            # Already uint8 (0-255) - use as is
            pass
        else:
            # Other integer types - convert to uint8
            marker_array = marker_array.astype(np.uint8)

        # Ensure it's 2D (some markers might be 1D)
        if marker_array.ndim == 1:
            # Assume square marker and reshape
            side_length = int(np.sqrt(marker_array.size))
            marker_array = marker_array.reshape(side_length, side_length)

        # Scale up the marker for better visibility (optional)
        scale_factor = 10  # Make it 10x larger
        scaled_marker = cv2.resize(marker_array, (marker_array.shape[1] * scale_factor, marker_array.shape[0] * scale_factor), interpolation=cv2.INTER_NEAREST)

        # Save using OpenCV for consistency
        import os
        os.makedirs(output_path, exist_ok=True)

        filename = f"{output_path}/apriltag_{marker_id}.png"
        cv2.imwrite(filename, scaled_marker)
        print(f"Saved AprilTag {marker_id} to {filename}")

        # Verify the saved image
        verify_img = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
        if verify_img is not None:
            print(f"Verification: saved image shape {verify_img.shape}, min: {verify_img.min()}, max: {verify_img.max()}")
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
    else:
        # Default: generate tags 0-10
        start_id = 0
        end_id = 10
        output_path = "apriltags"

    print(f"Generating AprilTags from ID {start_id} to {end_id-1}...")

    success_count = 0
    for marker_id in range(start_id, end_id):
        if save_apriltag(marker_id, output_path):
            success_count += 1

    print(f"Successfully generated {success_count} AprilTags")

if __name__ == "__main__":
    main()