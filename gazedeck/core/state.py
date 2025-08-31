# gazedeck/core/state.py

"""
State management for the Gazedeck application.
"""

from __future__ import annotations
from typing import Dict
from gazedeck.core.device_labeling import LabeledDevice

# In-process “global” storage for later pipelines (until app exits).
LABELED_DEVICES: Dict[int, LabeledDevice] = {}
