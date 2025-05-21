from transformers import pipeline
from PIL import Image
import torch
import os


# if __name__ == "__main__":
#     # Load the BLIP model
#     processor = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base", device=0 if torch.cuda.is_available() else -1)

#     # Load the image
image_path = "data/images_0000/Wilds_of_Eldraine_Commander/633370.jpg"  # Replace with your image path
image = Image.open(image_path)

#     # Generate caption
#     caption = processor(image, max_length=50, num_beams=4, do_sample=True)[0]['generated_text']

#     print("Generated Caption:", caption)
    
#     # # Save caption to a text file
#     # text_path = os.path.splitext(image_path)[0] + ".txt"
#     # with open(text_path, "w", encoding="utf-8") as txt_file:
#     #     txt_file.write(caption)

# from transformers import pipeline

captioner = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")
# txt = captioner("https://huggingface.co/datasets/Narsil/image_dummy/resolve/main/parrots.png")
txt = captioner(image)

print(txt)
## [{'generated_text': 'two birds are standing next to each other '}]

# Use a pipeline as a high-level helper
# from transformers import pipeline

from lmdeploy import pipeline, TurbomindEngineConfig, ChatTemplateConfig
from lmdeploy.vl import load_image

model = 'OpenGVLab/InternVL3-8B'
image = load_image('https://raw.githubusercontent.com/open-mmlab/mmdeploy/main/tests/data/tiger.jpeg')
pipe = pipeline(model, backend_config=TurbomindEngineConfig(session_len=16384, tp=1), chat_template_config=ChatTemplateConfig(model_name='internvl2_5'))
response = pipe(('describe this image', image))
print(response.text)

