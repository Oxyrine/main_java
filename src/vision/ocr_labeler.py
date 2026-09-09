"""
OCR room labeling and semantic room-type classification stage.
Degrades gracefully if Tesseract binary is not installed on PATH.
"""

from __future__ import annotations
import re
from typing import List, Tuple, Dict, Optional
import numpy as np

from src.vision.room_detector import RoomRegion

# Architectural room type mapping (supports English, Finnish, and common CAD abbreviations)
ROOM_TYPE_MAP: Dict[str, str] = {
    # English
    "LIVING": "living",
    "LIVINGROOM": "living",
    "BED": "bedroom",
    "BEDROOM": "bedroom",
    "KITCHEN": "kitchen",
    "BATH": "bathroom",
    "BATHROOM": "bathroom",
    "WC": "bathroom",
    "TOILET": "bathroom",
    "DINING": "dining",
    "DININGROOM": "dining",
    "OFFICE": "office",
    "STUDY": "office",
    "ENTRY": "entry",
    "HALL": "entry",
    "CORRIDOR": "entry",
    "BALCONY": "balcony",
    "TERRACE": "balcony",
    "STORAGE": "utility",
    "UTILITY": "utility",
    # Finnish
    "OH": "living",       # Olohuone
    "MH": "bedroom",      # Makuuhuone
    "K": "kitchen",       # Keittiö
    "KT": "kitchen",      # Keittiötila
    "ET": "entry",        # Eteinen
    "KHH": "utility",     # Kodinhoitohuone
    "PH": "bathroom",     # Pesuhuone
    "S": "sauna",         # Sauna
    "SAUNA": "sauna",
    "VH": "storage",      # Vaatehuone
    "VAR": "storage",     # Varasto
    "TK": "entry",        # Tuulikaappi
}


class RoomLabeler:
    """Labels room regions using OCR when available, falling back to positional names."""

    @staticmethod
    def is_available() -> bool:
        """Checks whether the Tesseract OCR engine is installed and available."""
        try:
            import pytesseract
            _ = pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def label(
        self,
        rooms: List[RoomRegion],
        thin_mask: np.ndarray,
        enable_ocr: bool = True,
        bgr_image: Optional[np.ndarray] = None,
    ) -> None:
        """
        Populates room.label and room.room_type for each detected room.
        Uses OCR when available and falls back to spatial and color heuristics.
        Mutates rooms in place.
        """
        ocr_ready = enable_ocr and self.is_available()
        h, w = thin_mask.shape[:2]

        for idx, room in enumerate(rooms, start=1):
            labeled = False
            if ocr_ready:
                rx, ry, rw, rh = room.bbox
                rx_i, ry_i = max(0, int(rx)), max(0, int(ry))
                rw_i, rh_i = int(rw), int(rh)
                crop = thin_mask[ry_i:min(h, ry_i + rh_i), rx_i:min(w, rx_i + rw_i)]

                extracted_text = self._ocr_crop(crop)
                if extracted_text:
                    norm_text = re.sub(r"[^A-Za-z0-9]", "", extracted_text.upper())
                    matched_type = "room"
                    for key, r_type in ROOM_TYPE_MAP.items():
                        if key in norm_text:
                            matched_type = r_type
                            break
                    room.label = extracted_text
                    room.room_type = matched_type
                    labeled = True

            if not labeled:
                r_type = "room"
                label = f"Room {idx}"

                if bgr_image is not None:
                    cx, cy = int(round(room.centroid[0])), int(round(room.centroid[1]))
                    sample = bgr_image[max(0, cy - 10):min(h, cy + 10), max(0, cx - 10):min(w, cx + 10)]
                    if sample.size > 0:
                        mean_bgr = np.mean(sample, axis=(0, 1))
                        # Blue wet-area fill: B > 200 and G < 210 and R < 210
                        is_blue = (mean_bgr[0] > 200 and mean_bgr[1] < 210 and mean_bgr[2] < 210)
                        if is_blue:
                            if room.area_px < 18000:
                                r_type = "sauna"
                                label = "Sauna"
                            elif room.area_px < 25000:
                                r_type = "bathroom"
                                label = "WC"
                            else:
                                r_type = "utility"
                                label = "PH/KHH"
                        else:
                            if room.area_px > 120000 or (room.centroid[0] > w * 0.5 and room.centroid[1] < h * 0.55):
                                r_type = "living"
                                label = "OH / K"
                            elif room.centroid[1] > h * 0.55:
                                r_type = "bedroom"
                                label = f"MH {idx}"
                            elif room.centroid[1] >= h * 0.3:
                                r_type = "entry"
                                label = "ET"
                else:
                    if room.centroid[1] > h * 0.55:
                        r_type = "bedroom"
                        label = f"MH {idx}"
                    elif room.centroid[0] > w * 0.5 and room.centroid[1] < h * 0.55:
                        r_type = "living"
                        label = "OH / K"
                    elif room.centroid[1] >= h * 0.3:
                        r_type = "entry"
                        label = "ET"

                room.label = label
                room.room_type = r_type

    def _ocr_crop(self, crop: np.ndarray) -> Optional[str]:
        """Runs pytesseract on image crop with psm 11 (sparse text)."""
        import cv2
        import pytesseract

        if crop.size == 0 or crop.shape[0] < 15 or crop.shape[1] < 15:
            return None

        # Text needs white background, dark foreground for standard Tesseract
        inv = cv2.bitwise_not(crop)
        try:
            config = "--psm 11 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
            txt = pytesseract.image_to_string(inv, config=config).strip()
            clean = " ".join(txt.split())
            return clean if len(clean) >= 2 else None
        except Exception:
            return None
