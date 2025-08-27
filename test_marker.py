#!/usr/bin/env python3

import cv2
import numpy as np

# Test reading the generated AprilTag
img = cv2.imread('apriltags/apriltag_0.png', cv2.IMREAD_GRAYSCALE)

if img is not None:
    print(f"Image shape: {img.shape}")
    print(f"Image dtype: {img.dtype}")
    print(f"Min value: {img.min()}, Max value: {img.max()}")
    print(f"Unique values: {np.unique(img)}")
    print("First few rows:")
    print(img[:10, :10])  # Show first 10x10 pixels

    # Display the image (if running in environment that supports it)
    cv2.imshow('AprilTag 0', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
else:
    print("Could not load image")
