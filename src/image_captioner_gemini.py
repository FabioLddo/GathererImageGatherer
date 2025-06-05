from google import genai
from google.genai import types
import json
import cv2 as cv
import numpy as np
import os
import backoff
from pathlib import Path
import logging
from PIL import Image
import matplotlib.pyplot as plt
from pydantic import BaseModel
import csv
from datetime import datetime
from google.genai.errors import ClientError
from google.genai.errors import ServerError
from typing import Dict
from tqdm.asyncio import tqdm_asyncio
import unicodedata
from write_captions import clean_unicode, generate_caption_from_metadata, cut_caption


SYSTEM_PROMPT = """
You are analyzing Magic: The Gathering card artwork for an AI training dataset. Create concise, descriptive captions that capture the essence, composition, and style of the fantasy artwork.

CAPTION STYLE:
Create a single flowing paragraph that captures:
1. Visual Elements
- Subject matter (creature, character, landscape, spell effect)
- Composition and focal point
- Color palette and lighting
- Art style and technique

2. Fantasy Elements
- Creature characteristics or character appearance
- Environmental/setting details
- Magical elements or effects
- Mood and atmosphere

IMPORTANT:
- One cohesive paragraph, maximum 100 tokens
- Focus on the visual artwork only, not card mechanics or rules
- Describe the most significant visual elements first
- Capture the fantasy atmosphere and mood
- Be specific but concise about colors, creatures, and magical elements
- Avoid speculation about card function or gameplay effects
"""

RESPONSE_SCHEMA = {
  "type": "object",
  "properties": {
    "caption": {
      "type": "string",
      "description": "Concise description of the card artwork (max 100 tokens)"
    },
    "subject_type": {
      "type": "string",
      "enum": ["creature", "character", "landscape", "spell/effect", "artifact", "multiple_elements"],
      "description": "Primary subject matter in the artwork"
    },
    "color_palette": {
      "type": "array",
      "items": {
        "type": "string"
      },
      "description": "Dominant colors in the artwork (2-4 colors)"
    },
    "mood": {
      "type": "string",
      "description": "Overall mood/atmosphere of the artwork"
    }
  },
  "required": [
    "caption",
    "subject_type",
    "color_palette",
    "mood"
  ]
}


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gemini_captioning.log'),
        logging.StreamHandler()
    ]
)


class CardArtCaptioner:
    def __init__(self, api_key: str, base_dir: str, version: str = "001"):
        self.base_dir = Path(base_dir)
        self.version = version
        # self.model_name = "gemini-1.5-pro"
        self.model_name = "gemini-2.0-flash"

        # Folders initialization
        # self.raw_dir = self.base_dir
        # self.dataset_dir = self.base_dir.parent / "captioned_dataset" / "dataset"
        # self.junk_dir = self.base_dir.parent / "captioned_dataset" / "junk"

        self.results_csv = self.base_dir / "gemini_captioning.csv"
        self.metadata_json = self.base_dir / "metadata.json"
        # self.metadata_csv = self.base_dir / "metadata.csv"

        # os.makedirs(self.dataset_dir, exist_ok=True)
        # os.makedirs(self.junk_dir, exist_ok=True)

        # Initialize Gemini client
        self.client = genai.Client(api_key=api_key)

        self.processed_files = self._load_processed_files()
        self._create_metadata()

    def _create_metadata(self):
        """Create or update metadata file"""
        if not self.metadata_json.exists():
            metadata = {
                "model": self.model_name,
                "date": datetime.now().isoformat(),
                "version": self.version,
                "system_prompt": SYSTEM_PROMPT,  # Global constant defined elsewhere
                "author": "Fabio Loddo",
            }
            with open(self.metadata_json, 'w') as f:
                json.dump(metadata, f, indent=2)

    def _load_processed_files(self) -> set:
        """Load list of already processed files from CSV"""
        processed = set()
        if self.results_csv.exists():
            with open(self.results_csv, 'r') as f:
                reader = csv.DictReader(f)
                processed.update(row['filename'] for row in reader)
        return processed

    @backoff.on_exception(
        backoff.expo,
        (Exception),
        max_tries=10,
        max_time=300
    )
    async def _analyze_image(self, image_path: Path, card_data: Dict) -> Dict:
        """Analyze single image with Gemini"""

        card_name = card_data.get('name', 'Unnamed Card')
        flavor_text = card_data.get('flavor_text', '')
        task = f"The card is named '{card_name}' and has the flavor text: '{flavor_text}'."

        # with open(image_path, 'rb') as f:
        #     image_bytes = f.read()

        # Open the image and crop it
        pil_image = Image.open(image_path)
        # conver rgba to rgb
        if pil_image.mode == "RGBA":
            r, g, b, a = pil_image.split()
            pil_image = Image.merge("RGB", (r, g, b))
        # shape
        # print(pil_image.size)
        cropped_image = self._crop_image_art(pil_image)
        # print(cropped_image.size)
        
        # Create a BytesIO object to store the image bytes
        from io import BytesIO
        buffer = BytesIO()
        cropped_image.save(buffer, format="JPEG")
        image_bytes = buffer.getvalue()

        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=[
                types.Part.from_text(text=SYSTEM_PROMPT),
                types.Part.from_text(text=task),
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            ],
            config=types.GenerateContentConfig(
                temperature=0.4,
                top_p=0.8,
                top_k=40,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA
            )
        )

        return json.loads(response.text)
    
    def _crop_image_art(self, img: Image) -> np.ndarray:
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

        return box_art
    

    def _generate_caption(self, image_path: Path, caption: str, card_data: dict) -> bool:
        """Generate the final caption combining model output and card data"""

        final_caption = generate_caption_from_metadata(card_data=card_data)

        # Add art description
        final_caption += f" Art description: {caption}"

        # Cut caption to last period if needed
        final_caption = cut_caption(final_caption)

        final_caption = clean_unicode(final_caption)

        caption_path = image_path.with_suffix('.txt')
        # Save caption to txt file
        with open(caption_path, 'w') as f:
            f.write(final_caption)

        return True
    
    # def _save_caption(self, image_path: Path, caption: dict, target_dir: Path):
    #     """Save caption to txt file"""

    #     final_caption = caption["caption"] + (f" This image features a {caption['shot_framing']} shot of "
    #                                           f"a {caption['garment_category']} garment, "
    #                                           f"captured from the {caption['view_angle']}. "
    #                                           f"Garment material is {caption['material']}")

    #     caption_path = target_dir / f"{image_path.stem}.txt"
    #     with open(caption_path, 'w') as f:
    #         f.write(final_caption)


    def _update_csv(self, filename: str, caption: str):
        """Update results CSV file"""
        file_exists = self.results_csv.exists()

        with open(self.results_csv, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['filename', 'caption'])
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                'filename': filename,
                'caption': caption
            })

    def _get_relative_path(self, path: Path) -> Path:
        """Convert absolute path to path relative to project root"""
        try:
            # Assuming self.base_dir's parent is the project root
            project_root = self.base_dir.parent.parent
            return path.relative_to(project_root)
        except ValueError:
            # If the path is not relative to project root, return the original path
            return path


    async def process_images(self):
        """Process all images"""
        # image_paths = [p for p in self.base_dir.glob('**/*.[jJ][pP][gG]') if p.name not in self.processed_files]
        # print(f"Found {len(image_paths)} images to process.")

        # Get all set directories
        set_dirs = [d for d in self.base_dir.glob('*') if d.is_dir()]
        print(f"Found {len(set_dirs)} sets to process.")
        
        # Get completion status for each set
        set_stats = {}
        for set_dir in set_dirs:
            set_name = set_dir.name
            all_images = list(set_dir.glob('*.[jJ][pP][gG]'))
            processed_images = [img for img in all_images if img.name in self.processed_files]
            
            total_count = len(all_images)
            processed_count = len(processed_images)
            completion_percent = (processed_count / total_count * 100) if total_count > 0 else 0
            
            set_stats[set_name] = {
                'total': total_count,
                'processed': processed_count,
                'completion': completion_percent
            }
            
            print(f"Set {set_name}: {processed_count}/{total_count} images captioned ({completion_percent:.2f}%)")
        
        # Find unprocessed images
        unprocessed_images = []
        for set_dir in set_dirs:
            for img_path in set_dir.glob('*.[jJ][pP][gG]'):
                if img_path.name not in self.processed_files:
                    unprocessed_images.append(img_path)
        
        print(f"Found {len(unprocessed_images)} unprocessed images across all sets.")
    
        async for image_path in tqdm_asyncio(unprocessed_images, desc="Processing images", unit="img"):
        # async for image_path in tqdm_asyncio(image_paths, desc="Processing images", unit="img"):
            try:

                json_path = image_path.with_suffix('.json')
                # load json data
                with open(json_path, 'r') as f:
                    card_data = json.load(f)

                result = await self._analyze_image(image_path, card_data)

                await asyncio.sleep(1)

                # target_dir = self.dataset_dir if result['valid'] else self.junk_dir

                # Copy image
                # shutil.copy2(image_path, target_dir / image_path.name)

                # Save caption


                # self._save_caption(image_path, result, target_dir)
                valid_caption = self._generate_caption(image_path, result, card_data) 
                if not valid_caption:
                    logging.info(f"Skipping {image_path.name} due to non-playable type.")
                    continue

                # Update CSV
                self._update_csv(
                    filename=image_path.name,
                    caption=result['caption']
                )

                self.processed_files.add(image_path.name)


                # Get set name from the image path
                set_name = image_path.parts[-2]  # The parent directory name
                
                # Update and log completion status for this set
                set_stats[set_name]['processed'] += 1
                set_stats[set_name]['completion'] = (set_stats[set_name]['processed'] / set_stats[set_name]['total'] * 100)
                
                if set_stats[set_name]['processed'] == set_stats[set_name]['total']:
                    logging.info(f"🎉 Set {set_name} is now completely captioned!")
                

                # logging.info(f"Successfully processed {image_path.name}")
                logging.info(f"Successfully processed {image_path}: {result['caption']}")


            except Exception as e:
                logging.error(f"Error processing {image_path.name}: {str(e)}")
                continue


async def main():
    # Configuration
    API_KEY = os.getenv("GEMINI_API_KEY")
    BASE_DIR = "/home/fabioloddo/repos/GathererImageGatherer/data/images"
    VERSION = "001"

    captioner = CardArtCaptioner(
        api_key=API_KEY,
        base_dir=BASE_DIR,
        version=VERSION
    )

    await captioner.process_images()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

    # TODO: add information for gemini to use as context, since it does not always understands the context of the image - done
    # TODO: add glob that divides for set, so that i have some full sets to train on - done