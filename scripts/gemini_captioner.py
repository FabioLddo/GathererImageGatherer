import csv
import json
import logging
import os
import shutil
import pandas as pd

from datetime import datetime
from pathlib import Path
from typing import Dict
from tqdm.asyncio import tqdm_asyncio

import backoff

from google import genai
from google.genai import types

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gemini_captioning.log'),
        logging.StreamHandler()
    ]
)

SYSTEM_PROMPT = """
You are analyzing fashion photos for an AI training dataset. Focus on validating human presence and creating rich, descriptive captions that capture style, composition, and garment presentation.
VALIDATION RULES:
Step 1: Check for Human Model
- Must see a person wearing clothes
- Product shots = invalid (probability 0.05)
- Mannequins = invalid (probability 0.05)
Step 2: Check Garment Type  
- Full garments = valid (probability 0.7-1.0)
- Only accessories = invalid (probability 0.05)
- Only detail shots = invalid (probability 0.05)
CAPTION STYLE:
Create a single flowing paragraph that captures:
1. Photography Elements
- Shot framing and angle (full-body/three-quarter/half-body/close-up)
- View direction (front/back/side/45-degree)
- Category of garment (upper body/lower body/full body)
- Studio lighting quality and mood
- Background treatment
2. Fashion Styling
- Model's pose and expression 
- Fitting 
- How garment interacts with body
- Movement and drape of fabrics
- Proportions and silhouette
- Color relationships and contrast
- Texture patterns
- Garment materials
- Notable design details, whether there are zips, pockets, buttons, logos
IMPORTANT:
- One cohesive paragraph, as close as possible 450 tokens
- Start with framing/angle description
- Only describe visible elements
- Avoid technical specifications
- Focus on styling and presentation
Since pictures are by Sh0ot1f1 brand, include always such information in the style.,
with the same choice of words, like: 'in the style of Sh0ot1f1{1}'.
"""


RESPONSE_SCHEMA = {
  "type": "object",
  "properties": {
    "caption": {
      "type": "string"
    },
    "shot_framing": {
          "type": "string"
    },
    "view_angle": {
      "type": "string"
    },
    "garment_category": {
      "type": "string"
    },
    "material": {
          "type": "string"
    },
    "valid": {
      "type": "boolean"
    },
    "probability": {
      "type": "number"
    },
  },
  "required": [
    "shot_framing",
    "caption",
    "view_angle",
    "garment_category",
    "material",
    "valid",
    "probability"
  ]
}


class FashionImageCaptioner:
    def __init__(self, api_key: str, base_dir: str, version: str = "001"):
        self.base_dir = Path(base_dir)
        self.version = version
        # self.model_name = "gemini-2.0-flash-exp"
        self.model_name = "gemini-1.5-pro"

        # Folders initialization
        self.raw_dir = self.base_dir
        self.dataset_dir = self.base_dir.parent / "captioned_dataset" / "dataset"
        self.junk_dir = self.base_dir.parent / "captioned_dataset" / "junk"
        self.results_csv = self.base_dir / "gemini_captioning.csv"
        self.metadata_json = self.base_dir / "metadata.json"
        self.metadata_csv = self.base_dir / "metadata.csv"

        os.makedirs(self.dataset_dir, exist_ok=True)
        os.makedirs(self.junk_dir, exist_ok=True)

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
                "author": "Felipe Cardoso"
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
    async def _analyze_image(self, image_path: Path) -> Dict:

        """Analyze single image with Gemini"""
        with open(image_path, 'rb') as f:
            image_bytes = f.read()

        task = self._extract_row_from_csv(image_path)

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

        # print(response.model_version)

        return json.loads(response.text)

    def _extract_row_from_csv(self, image_path):
        """Extract row from csv file and use it to create a request fo Gemini"""

        # Extract the filename of the image without the extension
        image_filename = os.path.splitext(os.path.basename(image_path))[0]
        image_id = image_filename.split("_")[0]

        # Read the CSV file into a DataFrame
        relative_path = image_path.relative_to(self.base_dir)
        csv_folder = relative_path.parts[0]

        csv_path = self.base_dir / Path(csv_folder) / "garments.csv"
        df = pd.read_csv(csv_path)

        # Find the row where the 'SKU' column matches the image filename
        matching_row = df[df['article_id'] == int(image_id)]
        task = (f"Caption the following image considering that the garment has the following properties."
                "Remember to mention the garment material in the final caption."
                f"Material: {matching_row['material'].values[0]}, "
                f"Description: {matching_row['description'].values[0]}, "
                f"Color: {matching_row['color'].values[0]}")

        return task

    def _save_caption(self, image_path: Path, caption: dict, target_dir: Path):
        """Save caption to txt file"""

        final_caption = caption["caption"] + (f" This image features a {caption['shot_framing']} shot of "
                                              f"a {caption['garment_category']} garment, "
                                              f"captured from the {caption['view_angle']}. "
                                              f"Garment material is {caption['material']}")

        caption_path = target_dir / f"{image_path.stem}.txt"
        with open(caption_path, 'w') as f:
            f.write(final_caption)

    def _update_csv(self, filename: str, valid: bool, probability: float, caption: str):
        """Update results CSV file"""
        file_exists = self.results_csv.exists()

        with open(self.results_csv, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['filename', 'valid', 'probability', 'caption'])
            if not file_exists:
                writer.writeheader()
            writer.writerow({
                'filename': filename,
                'valid': valid,
                'probability': probability,
                'caption': caption
            })

    async def process_images(self):
        """Process all images in raw directory"""
        image_paths = [p for p in self.raw_dir.glob('**/*.[jJ][pP][gG]') if p.name not in self.processed_files]
        print(f"Found {len(image_paths)} images to process.")
        async for image_path in tqdm_asyncio(image_paths, desc="Processing images", unit="img"):
            try:

                result = await self._analyze_image(image_path)

                await asyncio.sleep(1)

                target_dir = self.dataset_dir if result['valid'] else self.junk_dir

                # Copy image
                shutil.copy2(image_path, target_dir / image_path.name)

                # Save caption
                self._save_caption(image_path, result, target_dir)

                # Update CSV
                self._update_csv(
                    filename=image_path.name,
                    valid=result['valid'],
                    probability=result['probability'],
                    caption=result['caption']
                )

                self.processed_files.add(image_path.name)

                # logging.info(f"Successfully processed {image_path.name}")

            except Exception as e:
                logging.error(f"Error processing {image_path.name}: {str(e)}")
                continue


async def main():
    # Configuration
    API_KEY = os.getenv("GOOGLE_API_KEY")
    BASE_DIR = "/workdrive/data/datasets/HM/captions_selection/"
    VERSION = "001"

    captioner = FashionImageCaptioner(
        api_key=API_KEY,
        base_dir=BASE_DIR,
        version=VERSION
    )

    await captioner.process_images()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
