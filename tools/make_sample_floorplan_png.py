"""
Generates a clean synthetic residential floor-plan PNG with known ground truth.
Used for automated testing and regression verification of the CV pipeline.
"""

from pathlib import Path
import numpy as np


def create_sample_floorplan_png(output_path: Path) -> Path:
    """
    Renders a synthetic 1200x900 floor plan with 3 rooms, solid walls,
    door swing arcs, windows, and room labels.
    """
    import cv2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    h, w = 900, 1200
    # Create white canvas
    img = np.ones((h, w, 3), dtype=np.uint8) * 255

    # 1. Subtle pastel room fills
    # Room 1 (Living): x=[100, 600], y=[100, 800]
    img[100:800, 100:600] = [245, 250, 252]
    # Room 2 (Bedroom): x=[600, 1100], y=[100, 450]
    img[100:450, 600:1100] = [252, 248, 250]
    # Room 3 (Kitchen): x=[600, 1100], y=[450, 800]
    img[450:800, 600:1100] = [248, 252, 248]

    wall_color = (25, 25, 25)
    t = 16  # Wall thickness px (~160mm at 10mm/px)

    def draw_wall(p1, p2):
        cv2.line(img, p1, p2, wall_color, t)

    # 2. Draw walls with deliberate gaps for doors and windows
    # Top wall (y=100): Window at x=300..420
    draw_wall((100, 100), (300, 100))
    draw_wall((420, 100), (1100, 100))

    # Bottom wall (y=800): Entrance door at x=300..385
    draw_wall((100, 800), (300, 800))
    draw_wall((385, 800), (1100, 800))

    # Left wall (x=100): Continuous
    draw_wall((100, 100), (100, 800))

    # Right wall (x=1100): Window at y=200..320
    draw_wall((1100, 100), (1100, 200))
    draw_wall((1100, 320), (1100, 800))

    # Interior vertical partition (x=600): Door at y=250..335
    draw_wall((600, 100), (600, 250))
    draw_wall((600, 335), (600, 800))

    # Interior horizontal partition (y=450): Door at x=780..865
    draw_wall((600, 450), (780, 450))
    draw_wall((865, 450), (1100, 450))

    # 3. Thin-line details (doors and windows)
    thin_color = (60, 60, 60)

    # Window 1 (Top wall: x=300..420, y=100)
    cv2.line(img, (300, 96), (420, 96), thin_color, 2)
    cv2.line(img, (300, 104), (420, 104), thin_color, 2)

    # Window 2 (Right wall: x=1100, y=200..320)
    cv2.line(img, (1096, 200), (1096, 320), thin_color, 2)
    cv2.line(img, (1104, 200), (1104, 320), thin_color, 2)

    # Door 1 (Interior vertical wall: gap 250..335, hinge at 250, radius 85)
    # Arc swinging into room 2
    cv2.ellipse(img, (600, 250), (85, 85), 0, 0, 90, thin_color, 2)
    cv2.line(img, (600, 250), (685, 250), thin_color, 2)

    # Door 2 (Interior horizontal wall: gap 780..865, hinge at 780, radius 85)
    cv2.ellipse(img, (780, 450), (85, 85), 0, 90, 180, thin_color, 2)
    cv2.line(img, (780, 450), (780, 535), thin_color, 2)

    # Door 3 (Entrance door: bottom wall gap 300..385, hinge at 300, radius 85)
    cv2.ellipse(img, (300, 800), (85, 85), 0, 270, 360, thin_color, 2)
    cv2.line(img, (300, 800), (300, 715), thin_color, 2)

    # 4. Text labels
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img, "LIVING", (280, 450), font, 1.0, (50, 50, 50), 2, cv2.LINE_AA)
    cv2.putText(img, "BEDROOM", (780, 280), font, 1.0, (50, 50, 50), 2, cv2.LINE_AA)
    cv2.putText(img, "KITCHEN", (800, 640), font, 1.0, (50, 50, 50), 2, cv2.LINE_AA)

    cv2.imwrite(str(output_path), img)
    return output_path


if __name__ == "__main__":
    out = Path("fixtures/sample_floorplan.png")
    create_sample_floorplan_png(out)
    print(f"Created synthetic floor plan: {out.resolve()}")
