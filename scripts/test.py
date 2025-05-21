img = "/home/fabioloddo/repos/GathererImageGatherer/data/images/Adventures_in_the_Forgotten_Realms/527289.jpg"

# read image and plot
import cv2 
import PIL  
from PIL import Image
import io

# read image
# img_data = cv2.imread(img)

# # plot image
# cv2.imshow("image", image)
# cv2.waitKey(0)
# cv2.destroyAllWindows()

# try:
#     with Image.open(io.BytesIO(img_data)) as img:
#         img.verify()  # Check if it's a valid image
# except Exception as e:
#     print(f"Invalid image for: {e}")

# read image using PIL, check the mode(RGB, RGBA, etc.), the size and the format. then if it is rgba plot rgb image and alpha channel separately
img = Image.open(img)
img.show()
print(f"Image mode: {img.mode}")
print(f"Image size: {img.size}")
print(f"Image format: {img.format}")
# check if the image is RGBA
if img.mode == "RGBA":
    # split the image into RGB and alpha channels
    r, g, b, a = img.split()
    # plot the rgb image
    img_rgb = Image.merge("RGB", (r, g, b))
    img_rgb.show()
    # plot the alpha channel
    a.show()
else:
    # plot the image
    img.show()
