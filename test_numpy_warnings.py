#!/usr/bin/env python3
"""Test script to identify remaining numpy warning sources."""

import warnings
import numpy as np
import math
import random

# Enable all warnings as errors to catch them
warnings.filterwarnings('error', category=DeprecationWarning)

from gazedeck.core.mapping import GazeMapper
from gazedeck.core.homography_store import HomographyStore
from gazedeck.core.types import GazeSample

def test_mapping_warnings():
    """Test mapping functionality for numpy warnings."""
    print("Testing mapping functionality...")

    try:
        store = HomographyStore(ttl_ms=300, max_err_px=2.0, min_markers=3)
        mapper = GazeMapper(store)

        # Test homography comparison
        matrix1 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        matrix2 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
        result = mapper._get_homography_seq(matrix1)
        result = mapper._get_homography_seq(matrix2)  # This should trigger np.allclose
        print("✓ Homography comparison works without warnings")
        return True
    except DeprecationWarning as e:
        print(f"✗ Warning in mapping: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error in mapping: {e}")
        return False

def test_gaze_sample_creation():
    """Test GazeSample creation for numpy warnings."""
    print("Testing GazeSample creation...")

    try:
        # Test with various numeric types
        sample = GazeSample(
            ts_ms=1000,
            x=640.0,
            y=360.0,
            frame="scene_norm",
            conf=0.9
        )
        print("✓ GazeSample creation works without warnings")
        return True
    except DeprecationWarning as e:
        print(f"✗ Warning in GazeSample: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error in GazeSample: {e}")
        return False

def test_numpy_operations():
    """Test various numpy operations that might cause warnings."""
    print("Testing numpy operations...")

    try:
        # Test np.allclose
        arr1 = np.array([[1, 0], [0, 1]])
        arr2 = np.array([[1, 0], [0, 1]])
        result = np.allclose(arr1, arr2)
        bool_result = bool(result.item())  # Convert properly
        print("✓ np.allclose with .item() works without warnings")
        return True
    except DeprecationWarning as e:
        print(f"✗ Warning in numpy operations: {e}")
        return False
    except Exception as e:
        print(f"✗ Other error in numpy operations: {e}")
        return False

if __name__ == "__main__":
    print("=== Testing for NumPy Deprecation Warnings ===\n")

    results = []
    results.append(("Mapping", test_mapping_warnings()))
    results.append(("GazeSample", test_gaze_sample_creation()))
    results.append(("NumPy Ops", test_numpy_operations()))

    print("\n=== Summary ===")
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{name}: {status}")

    all_pass = all(results)
    print(f"\nOverall: {'✓ ALL TESTS PASS' if all_pass else '✗ SOME TESTS FAIL'}")
