import os
import cv2
from tqdm import tqdm
import shutil

# Set your root dataset directory here
dataset_dir = "/home/fabioloddo/repos/GathererImageGatherer/data/images"

# Gather all image paths
image_paths = []
for root, _, files in os.walk(dataset_dir):
    for file in files:
        if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff', '.webp')):
            image_paths.append(os.path.join(root, file))

unique_sizes = set()
corrupted_paths = []
missing_json = []
missing_txt = []

# Iterate with a progress bar
for path in tqdm(image_paths, desc="Processing images"):
    # Check image integrity
    image = cv2.imread(path)
    if image is None:
        corrupted_paths.append(path)
    else:
        height, width, _ = image.shape
        unique_sizes.add((width, height))

    # Check if corresponding .json and .txt files exist
    base_path, ext = os.path.splitext(path)
    json_path = base_path + ".json"
    txt_path = base_path + ".txt"

    if not os.path.exists(json_path):
        missing_json.append(json_path)
    if not os.path.exists(txt_path):
        missing_txt.append(txt_path)

# Report image size summary
print("\n✅ Unique image sizes:")
for size in sorted(unique_sizes):
    print(f" - {size}")

# Report corrupted images
if corrupted_paths:
    print(f"\n❌ Corrupted or unreadable images ({len(corrupted_paths)}):")
    for path in corrupted_paths:
        print(f" - {path}")

# Report missing .json files
if missing_json:
    print(f"\n📁 Missing .json files for {len(missing_json)} images:")
    for path in missing_json:
        print(f" - {path}")

# Report missing .txt files
if missing_txt:
    print(f"\n📁 Missing .txt files for {len(missing_txt)} images:")
    for path in missing_txt:
        print(f" - {path}")

# remove the images missing the json
for path in missing_json:
    image_path = path.replace('.json', '.jpg')
    if os.path.exists(image_path):
        os.remove(image_path)
        print(f'Image removed: {image_path}')


# If there are problems, attempt to show them
# if corrupted_paths:
#     print("\nCorrupted or unreadable images:")
#     for path in corrupted_paths:
#         print(path)
#         corrupted_img = cv2.imread(path)
#         if corrupted_img is not None:
#             cv2.imshow(f"Corrupted Image: {path}", corrupted_img)
#             cv2.waitKey(0)
#             cv2.destroyAllWindows()