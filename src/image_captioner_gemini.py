from google import genai
from google.genai import types
import openai
import json
import cv2 as cv
import numpy as np
import os
import PIL
import base64

from transformers import BlipProcessor, BlipForConditionalGeneration
from PIL import Image
import matplotlib.pyplot as plt

import time
from google.genai.errors import ClientError
from google.genai.errors import ServerError

# Only run this block for Gemini Developer API
client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

openai.api_key = os.environ["OPENAI_API_KEY"]

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


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


def box_art(img):
    """
    Cut out the box art from the image.
    """


    # Define the box art area (example coordinates)
    # size = (370, 265, 3)
    left = 20
    top = 40
    right = img.width - left
    bottom = img.height - 160

    # Crop the image to the box art area
    box_art = img.crop((left, top, right, bottom))

        # Use proportional values
    left = int(img.width * 0.07)
    top = int(img.height * 0.11)
    right = int(img.width * 0.93)
    bottom = int(img.height * 0.56)

    box_art = img.crop((left, top, right, bottom))


    # Save or return the cropped image
    box_art.save("box_art.png")
    return np.array(box_art)


def gemini_captioner(image_path, api_key):

    client = genai.Client(api_key=api_key)

    # my_file = client.files.upload(file=image_path)

    # response = client.models.generate_content(
    #     model="gemini-2.0-flash",
    #     contents=[my_file, "Caption the art of this Magic the Gathering image."],
    # )

    # prompt = """List a few popular cookie recipes in JSON format.

    # Use this JSON schema:

    # Recipe = {'recipe_name': str, 'ingredients': list[str]}
    # Return: list[Recipe]"""
    # my_prompt = (
    # "You are an expert art critic specializing in fantasy illustrations. "
    # "Describe this cropped artwork from a Magic: The Gathering card in vivid detail. "
    # "Focus on: "
    # "1. The central figure(s) or subject(s): their appearance, attire, species (e.g., human, elf, dragon, beast). "
    # "2. The setting or background: environment, notable features, atmosphere. "
    # "3. Any visible action or magical effects: spells, combat, movement. "
    # "4. The overall mood and artistic style: e.g., dark, ethereal, dynamic, painterly. "
    # "Provide a comprehensive and evocative description in a single text corpus."
    # )
    
    # with open(image_path, 'rb') as f:
    #     image_bytes = f.read()

    from pydantic import BaseModel

    class Recipe(BaseModel):
        caption: str
        # tags: list[str]

    image_bytes = encode_image(image_path)

    response = client.models.generate_content(
    model='gemini-2.0-flash',
    contents=[
    types.Part.from_bytes(
        data=image_bytes,
        mime_type='image/png',
    ),
    # my_prompt
    # "Provide a description of the features of the art in single short paragraph. "
    # 'I need a caption that describes the image in single short paragraph, focus on subjects, background and colors, avoid useless informations.'
    'I need a caption that describes the image in a short paragraph, focus on the main image features, avoid useless informations.'

    ],
    config={
    "response_mime_type": "application/json",
    "response_schema": Recipe,
    },
    )

    # print(response.text)

    return response.text


def main():
    # cycle trough all images for all sets and generate captions to append to text files
    sets = os.listdir("data/images/")
    MAX_RETRIES = 3
    SLEEP_SECONDS = 30

    for set in sets:
        for image_name in os.listdir(os.path.join("data/images/", set)):
            if not any(image_name.lower().endswith(ext) for ext in ('.png', '.jpg', '.jpeg', '.bmp')):
                continue
            image_path = os.path.join("data/images/", set, image_name)
            img = Image.open(image_path)
            cropped_art = box_art(img)

            temp_cropped_path = f"./temp/temp_box_art_{image_name}"
            Image.fromarray(cropped_art).save(temp_cropped_path, "PNG")

            # Retry logic
            caption = None
            for attempt in range(MAX_RETRIES):
                try:
                    caption = gemini_captioner(temp_cropped_path, os.environ["GEMINI_API_KEY"])
                    response = json.loads(caption)
                    break
                except ClientError as e:
                    if e.code == 429:
                        print("Rate limit hit, retrying...")
                        time.sleep(SLEEP_SECONDS)
                    else:
                        raise e
                except ServerError as e:
                    print(f"Server error: {e}, retrying...")
                    time.sleep(SLEEP_SECONDS)

            if response:
                text_path = os.path.splitext(image_path)[0] + ".txt"
                with open(text_path, "a", encoding="utf-8") as txt_file:
                    txt_file.write(f"\nArt description: {response.get('caption', '')}\n")
                print(f"Caption for {image_name} saved to {text_path}")

            os.remove(temp_cropped_path)


if __name__ == "__main__":
    main()

    # image_path = "data/images/Alara_Reborn/144249.jpg"

    # # Open the image
    # img = Image.open(image_path)

    # plt.imshow(img)
    # plt.axis('off')  # Hide the axes
    # plt.show()

    # bb = box_art(img)

    # plt.imshow(np.array(bb))
    # plt.axis('off')  # Hide the axes
    # plt.show()

    # text = gemini_captioner("box_art.png", os.environ["GEMINI_API_KEY"])

    # text = json.loads(text)

    # print(text.get("caption"))


