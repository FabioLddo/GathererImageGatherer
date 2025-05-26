from google import genai
from google.genai import types
import openai
import json
import cv2 as cv
import numpy as np
import os
import backoff
import shutil
import base64
from pathlib import Path
import logging
from transformers import BlipProcessor, BlipForConditionalGeneration
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

def clean_unicode(text: str) -> str:
    # Normalize Unicode to NFKD form and encode to ASCII
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


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


    def _generate_caption(self, image_path: Path, caption: Dict, card_data: Dict) -> bool:
        """
        Args:
            card_data (dict): A dictionary representing the card's JSON data.

        Returns:
            str: A descriptive caption for the card.
        """

        if not isinstance(card_data, dict):
            print("Error: Input must be a dictionary.")
            return None

        # --- Extract Key Information ---
        name = card_data.get('name', 'Unnamed Card')
        type_line = card_data.get('type_line', 'Unknown Type')
        mana_cost = card_data.get('mana_cost', '')
        colors = card_data.get('colors', [])
        color_identity = card_data.get('color_identity', [])
        oracle_text = card_data.get('oracle_text', '')
        flavor_text = card_data.get('flavor_text', '')
        artist = card_data.get('artist', 'Unknown Artist')
        set_name = card_data.get('set_name', 'Unknown Set')
        rarity = card_data.get('rarity', 'Unknown Rarity')
        power = card_data.get('power', None)
        toughness = card_data.get('toughness', None)

        # if any of the following types is present in the type_line, skip the caption
        non_playable_types = ['Class', 'Basic Land', 'Artifact', 'Token', 'Emblem', 'Double-faced', 'Land', 'Dungeon', 'Conspiracy', 'Phenomenon', 'Plane', 'Scheme', 'Vanguard', 'Attraction']
        if any(nt in type_line for nt in non_playable_types):
            return False

        # --- Determine Color Description ---
        color_source = colors if colors else color_identity
        if color_source:
            color_map = {'W': 'White', 'U': 'Blue', 'B': 'Black', 'R': 'Red', 'G': 'Green'}
            color_names = [color_map.get(c, c) for c in color_source]
            if len(color_names) > 1:
                color_description = f"{', '.join(color_names[:-1])} and {color_names[-1]}"
            else:
                color_description = color_names[0]
        elif "Land" in type_line or not mana_cost:
            color_description = "Colorless"
        else:
            color_description = "Colorless"

        # --- Build the Caption ---
        description_parts = []

        # Core identity
        description_parts.append(f"Magic: The Gathering card art for '{name}', a {color_description} {type_line}.")

        # Add mana cost
        if mana_cost:
            description_parts.append(f"Mana Cost: {mana_cost}.")

        # Add oracle text and flavor text
        if flavor_text:
            description_parts.append(f"The card evokes themes of: \"{flavor_text}\".")
        if oracle_text:
            description_parts.append(f"The card text mentions: \"{oracle_text}\".")


        # Add power/toughness if available
        if power is not None and toughness is not None:
            description_parts.append(f"Power/Toughness: {power}/{toughness} (can deal {power} damage and take {toughness} damage).")

        # Add artist, set, and rarity
        description_parts.append(f"Artwork by {artist}, from the '{set_name}' set.")
        description_parts.append(f"Rarity: {rarity}.")

        # Mention colors explicitly
        if colors:
            color_list = ', '.join(colors)
            description_parts.append(f"Colors: {color_list}.")

        # --- Combine into final caption ---
        final_caption = " ".join(description_parts)

        # add art description
        final_caption += f" Art description: {caption['caption']}"

        # convert all to utf-8
        # final_caption = final_caption.encode('utf-8', 'ignore').decode('utf-8').replace("\u2014", "-")
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