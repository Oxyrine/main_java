"""
Image preprocessing stage: deskewing, content-cropping, and downscaling.
"""

from __future__ import annotations
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Optional
import numpy as np


@dataclass
class PreparedImage:
    """Preprocessed image ready for computer-vision feature extraction."""
    bgr: np.ndarray
    gray: np.ndarray
    scale_factor: float        # original_px / working_px
    crop_offset: Tuple[int, int]  # (x, y) offset in original image
    orig_w: int
    orig_h: int
    working_w: int
    working_h: int


class ImagePreprocessor:
    """Handles loading, deskewing, content-area cropping, and normalization."""

    def __init__(self, max_dim: int = 1600):
        self.max_dim = max_dim

    def run(self, image_path: Path | str) -> PreparedImage:
        """Loads and preprocesses image from path."""
        import cv2

        path_str = str(image_path)
        img = cv2.imread(path_str)
        if img is None:
            raise FileNotFoundError(f"Failed to load image from: {path_str}")

        orig_h, orig_w = img.shape[:2]

        # 1. Deskew (if significant rotation detected)
        deskewed = self._deskew(img)

        # 2. Content Crop (removes empty borders, legends, title blocks)
        cropped, crop_x, crop_y = self._content_crop(deskewed)

        # 3. Scale to normalized working size
        crop_h, crop_w = cropped.shape[:2]
        max_size = max(crop_w, crop_h)
        if max_size > self.max_dim:
            scale = self.max_dim / float(max_size)
            new_w = int(round(crop_w * scale))
            new_h = int(round(crop_h * scale))
            working_bgr = cv2.resize(cropped, (new_w, new_h), interpolation=cv2.INTER_AREA)
            scale_factor = 1.0 / scale
        elif max_size < 400:
            target_dim = 900.0
            scale = target_dim / float(max_size)
            new_w = int(round(crop_w * scale))
            new_h = int(round(crop_h * scale))
            working_bgr = cv2.resize(cropped, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            scale_factor = 1.0 / scale
        else:
            working_bgr = cropped
            scale_factor = 1.0

        working_gray = cv2.cvtColor(working_bgr, cv2.COLOR_BGR2GRAY)
        wh, ww = working_bgr.shape[:2]

        return PreparedImage(
            bgr=working_bgr,
            gray=working_gray,
            scale_factor=scale_factor,
            crop_offset=(crop_x, crop_y),
            orig_w=orig_w,
            orig_h=orig_h,
            working_w=ww,
            working_h=wh,
        )

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """Estimates and corrects rotation angle if > 0.5 degrees."""
        import cv2

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=80, maxLineGap=10)

        if lines is None or len(lines) < 4:
            return img

        angles = []
        for line in lines:
            x1, y1, x2, y2 = line.ravel()[:4]
            deg = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180.0
            # Fold to nearest horizontal or vertical: deviation from 0, 90, 180
            dev_h = deg if deg <= 45 else (deg - 180 if deg >= 135 else None)
            dev_v = (deg - 90) if 45 < deg < 135 else None
            dev = dev_h if dev_h is not None else dev_v
            if dev is not None and abs(dev) < 15.0:
                angles.append(dev)

        if not angles:
            return img

        median_angle = float(np.median(angles))
        if abs(median_angle) < 0.5:
            return img

        # Rotate around center
        h, w = img.shape[:2]
        center = (w // 2, h // 2)
        matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
        deskewed = cv2.warpAffine(img, matrix, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return deskewed

    def _content_crop(self, img: np.ndarray) -> Tuple[np.ndarray, int, int]:
        """Detects bounding box of architectural content and crops out margins."""
        import cv2

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Ink detection: pixels darker than light background
        ink = (gray < 235).astype(np.uint8) * 255

        # If image is mostly dark (inverted/dark mode blueprint), invert it
        if np.mean(gray) < 128:
            ink = (gray > 30).astype(np.uint8) * 255

        # Morph close to unify floorplan elements
        ksize = max(5, int(min(img.shape[:2]) * 0.02))
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (ksize, ksize))
        closed = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return img, 0, 0

        # Find bounding box of all significant ink
        h, w = img.shape[:2]
        min_area = (w * h) * 0.05
        significant = [c for c in contours if cv2.contourArea(c) > min_area]

        if not significant:
            # Fall back to largest contour
            largest = max(contours, key=cv2.contourArea)
            x, y, cw, ch = cv2.boundingRect(largest)
        else:
            # Union of significant contours
            x_min = min(cv2.boundingRect(c)[0] for c in significant)
            y_min = min(cv2.boundingRect(c)[1] for c in significant)
            x_max = max(cv2.boundingRect(c)[0] + cv2.boundingRect(c)[2] for c in significant)
            y_max = max(cv2.boundingRect(c)[1] + cv2.boundingRect(c)[3] for c in significant)
            x, y, cw, ch = x_min, y_min, x_max - x_min, y_max - y_min

        # Add 15px padding
        pad = 15
        x0 = max(0, x - pad)
        y0 = max(0, y - pad)
        x1 = min(w, x + cw + pad)
        y1 = min(h, y + ch + pad)

        # Only crop if it removes at least 5% border
        if (x1 - x0) < w * 0.98 or (y1 - y0) < h * 0.98:
            return img[y0:y1, x0:x1], x0, y0

        return img, 0, 0
