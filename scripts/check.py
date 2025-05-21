# filepath: /home/fabioloddo/repos/GathererImageGatherer/src/check.py
import os
import cv2
from tqdm import tqdm

# Set your root dataset directory here
dataset_dir = "/home/fabioloddo/repos/GathererImageGatherer/data/images"

# Gather all image paths first
image_paths = []
for root, _, files in os.walk(dataset_dir):
    for file in files:
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')):
            image_paths.append(os.path.join(root, file))

unique_sizes = set()
corrupted_paths = []

# Iterate with a progress bar
for path in tqdm(image_paths, desc="Processing images"):
    image = cv2.imread(path)
    if image is None:
        corrupted_paths.append(path)
    else:
        height, width, _ = image.shape
        unique_sizes.add((width, height))

# Print all unique image sizes found
print("Unique image sizes:")
for size in sorted(unique_sizes):
    print(size)

# If there are problems, attempt to show them
if corrupted_paths:
    print("\nCorrupted or unreadable images:")
    for path in corrupted_paths:
        print(path)
        corrupted_img = cv2.imread(path)
        if corrupted_img is not None:
            cv2.imshow(f"Corrupted Image: {path}", corrupted_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
