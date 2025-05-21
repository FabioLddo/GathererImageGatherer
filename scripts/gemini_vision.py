import base64
from openai import OpenAI
import os
import openai
import numpy as np
import cv2 as cv
from PIL import Image
import json


def display(image, window_name="display", width=None, height=None, wait_key=0):
    def mouse_callback(event, x, y, flags, param):
        if event == cv.EVENT_MOUSEMOVE:
            pixel_value = image[y, x]
            cv.setWindowTitle(window_name, f"({x}, {y}): {pixel_value}")

    h, w = image.shape[:2]
    if width is None and height is None:
        dim = (w, h)
    elif width is None:
        ratio = height / float(h)
        dim = (int(w * ratio), height)
    else:
        ratio = width / float(w)
        dim = (width, int(h * ratio))

    cv.namedWindow(window_name, cv.WINDOW_NORMAL)
    cv.resizeWindow(window_name, dim[0], dim[1]) # resize window
    cv.setMouseCallback(window_name, mouse_callback)
    cv.imshow(window_name, image)
    cv.waitKey(wait_key)
    cv.destroyWindow(window_name)


def box_art(image_path):
    """
    Cut out the box art from the image.
    """
    from PIL import Image

    # Open the image
    img = Image.open(image_path)

    # Define the box art area (example coordinates)
    size = (370, 265, 3)
    left = 20
    top = 40
    right = img.width - left
    bottom = img.height - 160

    # Crop the image to the box art area
    box_art = img.crop((left, top, right, bottom))

    display(np.array(box_art), "Box Art")

        # Use proportional values
    left = int(img.width * 0.07)
    top = int(img.height * 0.11)
    right = int(img.width * 0.93)
    bottom = int(img.height * 0.56)

    box_art = img.crop((left, top, right, bottom))
    display(np.array(box_art), "Box Art")

    # Save or return the cropped image
    box_art.save("box_art.png")
    return np.array(box_art)



openai.api_key = os.environ["OPENAI_API_KEY"]

client = OpenAI()

# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# Path to your image
image_path = "data/images/Wilds_of_Eldraine_Commander/633370.jpg"

# Getting the Base64 string
base64_image = encode_image(image_path)


response = client.responses.create(
    model="gpt-4.1",
    input=[
        {
            "role": "user",
            "content": [
                { "type": "input_text", "text": "what's in this image?" },
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}",
                },
            ],
        }
    ],
)

print(response.output_text)