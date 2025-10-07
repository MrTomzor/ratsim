import cv2
import numpy as np

# Load image with alpha channel
img = cv2.imread("obstacles_old.png", cv2.IMREAD_UNCHANGED)

# Extract obstacle mask (black pixels with alpha > 0)
# You can adapt this depending on your format
if img.shape[2] == 4:
    alpha = img[:, :, 3]
else:
    alpha = np.ones(img.shape[:2], dtype=np.uint8) * 255

# Consider black where (R,G,B) all near 0 and alpha > 0
obstacle_mask = (np.all(img[:, :, :3] < 10, axis=2)) & (alpha > 0)
obstacle_mask = obstacle_mask.astype(np.uint8) * 255

# Morphological edge extraction
kernel = np.ones((3, 3), np.uint8)
eroded = cv2.erode(obstacle_mask, kernel, iterations=1)
edges = obstacle_mask - eroded

# Optional: clean up noise
# edges = cv2.medianBlur(edges, 3)

# Save or display result
# Create RGBA output: black where edges, transparent elsewhere
output = np.zeros((edges.shape[0], edges.shape[1], 4), dtype=np.uint8)
output[:, :, 0:3] = 0  # black color
output[:, :, 3] = edges  # alpha = edges (255 on edges, 0 elsewhere)

# Save the result as PNG (keeps transparency)
cv2.imwrite("edges.png", output)
# cv2.imwrite("edges.png", edges)
cv2.imshow("Obstacle Edges", edges)
while True:
    if cv2.waitKey(1) & 0xFF == 27:  # Press 'ESC' to exit
        break
# cv2.waitKey(0)
# cv2.destroyAllWindows()
