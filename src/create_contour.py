import cv2
import numpy as np

# Load the image
image_path = "data/images_0001/Adventures_in_the_Forgotten_Realms/527289.jpg"
image = cv2.imread(image_path)

# Convert to grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Apply Gaussian blur to reduce noise
blurred = cv2.GaussianBlur(gray, (5, 5), 0)

# Apply Canny edge detection
edges = cv2.Canny(blurred, 50, 150)

# Optional: thicken the edges if needed
# kernel = np.ones((2, 2), np.uint8)
# thicker_edges = cv2.dilate(edges, kernel, iterations=1)

# Save the contour image
cv2.imwrite("card_contour.png", edges)