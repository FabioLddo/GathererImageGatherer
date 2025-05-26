import json
import logging
import csv
from pathlib import Path
from datetime import datetime
from PIL import Image
import torch
import torchvision.transforms as T
from torchvision.transforms.functional import InterpolationMode
from transformers import AutoModel, AutoTokenizer

from tqdm.asyncio import tqdm_asyncio

import unicodedata

def clean_unicode(text: str) -> str:
    # Normalize Unicode to NFKD form and encode to ASCII
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('intern_captioning.log'),
        logging.StreamHandler()
    ]
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Simplified prompt for the InternVL model
# SYSTEM_PROMPT = """You are analyzing Magic: The Gathering card artwork. Create a concise, descriptive caption 
# that captures the visual elements, composition, color palette, style, fantasy elements, and mood of the artwork. 
# Focus only on the visual aspects, not card mechanics. Keep your response under 100 tokens."""

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

class InternVLCardArtCaptioner:
    def __init__(self, base_dir: str, model_path: str = 'OpenGVLab/InternVL2-8B', version: str = "001"):
        self.base_dir = Path(base_dir)
        self.version = version
        self.model_path = model_path
        self.model_name = "InternVL2-8B"

        # Folders initialization
        self.results_csv = self.base_dir / "intern_captioning.csv"
        self.metadata_json = self.base_dir / "metadata.json"

        # Load model and tokenizer
        self._load_model()
        
        self.processed_files = self._load_processed_files()
        self._create_metadata()

    # def _load_model(self):
    #     """Load the InternVL model and tokenizer"""
    #     # Define device map for model
    #     device_map = self._split_model(self.model_name)
        
    #     # Load model with optimizations
    #     self.model = AutoModel.from_pretrained(
    #         self.model_path,
    #         torch_dtype=torch.bfloat16,
    #         load_in_8bit=False,
    #         low_cpu_mem_usage=True,
    #         use_flash_attn=True,
    #         trust_remote_code=True,
    #         device_map=device_map).eval()
        
    #     self.tokenizer = AutoTokenizer.from_pretrained(
    #         self.model_path, 
    #         trust_remote_code=True, 
    #         use_fast=False
    #     )
        
    #     # Set generation config
    #     self.generation_config = dict(max_new_tokens=128, do_sample=True)

        # Load InterVL2-8B model, only need 24G VRAM,if you wanna to load bigger models like 26B or 72B,you should need 1-3 80G A100
    def _load_model(self, model_name_or_path="OpenGVLab/InternVL2-8B"):
        model = (
            AutoModel.from_pretrained(
                model_name_or_path,
                torch_dtype=torch.bfloat16,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
            )
            .eval()
            .to(device)
        )

        self.model = model

        tokenizer = AutoTokenizer.from_pretrained(
            model_name_or_path, trust_remote_code=True, use_fast=False
        )

        self.tokenizer = tokenizer

        # Set generation config
        self.generation_config = dict(max_new_tokens=128, do_sample=True)

        return (model, tokenizer)


    def _create_metadata(self):
        """Create or update metadata file"""
        if not self.metadata_json.exists():
            metadata = {
                "model": self.model_name,
                "date": datetime.now().isoformat(),
                "version": self.version,
                "system_prompt": SYSTEM_PROMPT,
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

    def _load_image(self, image_path, input_size=448, max_num=12):
        """Load and preprocess image for InternVL"""
        image = Image.open(image_path).convert('RGB')
        image = self._crop_image_art(image)
        transform = self._build_transform(input_size=input_size)
        images = self._dynamic_preprocess(image, image_size=input_size, use_thumbnail=True, max_num=max_num)
        pixel_values = [transform(image) for image in images]
        pixel_values = torch.stack(pixel_values)
        return pixel_values.to(torch.bfloat16).cuda()
    
    def _build_transform(self, input_size):
        """Build image transform"""
        IMAGENET_MEAN = (0.485, 0.456, 0.406)
        IMAGENET_STD = (0.229, 0.224, 0.225)
        transform = T.Compose([
            T.Lambda(lambda img: img.convert('RGB') if img.mode != 'RGB' else img),
            T.Resize((input_size, input_size), interpolation=InterpolationMode.BICUBIC),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD)
        ])
        return transform
    
    def _find_closest_aspect_ratio(self, aspect_ratio, target_ratios, width, height, image_size):
        """Find closest aspect ratio for image preprocessing"""
        best_ratio_diff = float('inf')
        best_ratio = (1, 1)
        area = width * height
        for ratio in target_ratios:
            target_aspect_ratio = ratio[0] / ratio[1]
            ratio_diff = abs(aspect_ratio - target_aspect_ratio)
            if ratio_diff < best_ratio_diff:
                best_ratio_diff = ratio_diff
                best_ratio = ratio
            elif ratio_diff == best_ratio_diff:
                if area > 0.5 * image_size * image_size * ratio[0] * ratio[1]:
                    best_ratio = ratio
        return best_ratio
    
    def _dynamic_preprocess(self, image, min_num=1, max_num=12, image_size=448, use_thumbnail=False):
        """Preprocess image with dynamic aspect ratio handling"""
        orig_width, orig_height = image.size
        aspect_ratio = orig_width / orig_height

        # Calculate the existing image aspect ratio
        target_ratios = set(
            (i, j) for n in range(min_num, max_num + 1) for i in range(1, n + 1) for j in range(1, n + 1) if
            i * j <= max_num and i * j >= min_num)
        target_ratios = sorted(target_ratios, key=lambda x: x[0] * x[1])

        # Find the closest aspect ratio to the target
        target_aspect_ratio = self._find_closest_aspect_ratio(
            aspect_ratio, target_ratios, orig_width, orig_height, image_size)

        # Calculate the target width and height
        target_width = image_size * target_aspect_ratio[0]
        target_height = image_size * target_aspect_ratio[1]
        blocks = target_aspect_ratio[0] * target_aspect_ratio[1]

        # Resize the image
        resized_img = image.resize((target_width, target_height))
        processed_images = []
        for i in range(blocks):
            box = (
                (i % (target_width // image_size)) * image_size,
                (i // (target_width // image_size)) * image_size,
                ((i % (target_width // image_size)) + 1) * image_size,
                ((i // (target_width // image_size)) + 1) * image_size
            )
            # Split the image
            split_img = resized_img.crop(box)
            processed_images.append(split_img)
        assert len(processed_images) == blocks
        if use_thumbnail and len(processed_images) != 1:
            thumbnail_img = image.resize((image_size, image_size))
            processed_images.append(thumbnail_img)
        return processed_images

    def _crop_image_art(self, img: Image) -> Image:
        """Cut out the box art from the image."""
        # Use proportional values
        left = int(img.width * 0.07)
        top = int(img.height * 0.11)
        right = int(img.width * 0.93)
        bottom = int(img.height * 0.56)

        box_art = img.crop((left, top, right, bottom))
        return box_art

    async def _analyze_image(self, image_path: Path, card_data: dict) -> str:
        """Analyze single image with InternVL"""
        card_name = card_data.get('name', 'Unnamed Card')
        flavor_text = card_data.get('flavor_text', '')
        
        # Prepare prompt
        prompt = f"<image>\nThis is a Magic: The Gathering card named '{card_name}'."
        if flavor_text:
            prompt += f" It has the flavor text: '{flavor_text}'."
        prompt += f" {SYSTEM_PROMPT}"
        
        # Load and preprocess image
        pixel_values = self._load_image(image_path)
        
        # Generate caption
        response = self.model.chat(self.tokenizer, pixel_values, prompt, self.generation_config)
        
        # Remove any trailing or leading quotes
        caption = response.strip('" \t\n')
        
        return caption

    def _generate_caption(self, image_path: Path, caption: str, card_data: dict) -> bool:
        """Generate the final caption combining model output and card data"""
        if not isinstance(card_data, dict):
            print("Error: Input must be a dictionary.")
            return False

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

        # If any of the following types is present in the type_line, skip the caption
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
            description_parts.append(f"Power/Toughness: {power}/{toughness}.")

        # Add artist, set, and rarity
        description_parts.append(f"Artwork by {artist}, from the '{set_name}' set.")
        description_parts.append(f"Rarity: {rarity}.")

        # --- Combine into final caption ---
        final_caption = " ".join(description_parts)

        # Add art description
        final_caption += f" Art description: {caption}"

        # convert all to utf-8
        # final_caption = final_caption.encode('utf-8', 'ignore').decode('utf-8').replace("\u2014", "-")

        final_caption = clean_unicode(final_caption)

        caption_path = image_path.with_suffix('.txt')
        # Save caption to txt file
        with open(caption_path, 'w') as f:
            f.write(final_caption)

        return True

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

    async def process_images(self):
        """Process all images"""
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
            try:
                json_path = image_path.with_suffix('.json')
                # Load json data
                with open(json_path, 'r') as f:
                    card_data = json.load(f)

                # caption = self._analyze_image(image_path, card_data)

                caption = await self._analyze_image(image_path, card_data)

                await asyncio.sleep(1)

                # Generate and save caption
                valid_caption = self._generate_caption(image_path, caption, card_data) 
                if not valid_caption:
                    logging.info(f"Skipping {image_path.name} due to non-playable type.")
                    continue

                # Update CSV
                self._update_csv(
                    filename=image_path.name,
                    caption=caption
                )

                self.processed_files.add(image_path.name)

                # Get set name from the image path
                set_name = image_path.parts[-2]  # The parent directory name
                
                # Update and log completion status for this set
                set_stats[set_name]['processed'] += 1
                set_stats[set_name]['completion'] = (set_stats[set_name]['processed'] / set_stats[set_name]['total'] * 100)
                
                if set_stats[set_name]['processed'] == set_stats[set_name]['total']:
                    logging.info(f"🎉 Set {set_name} is now completely captioned!")

                logging.info(f"Successfully processed {image_path}: {caption}")

            except Exception as e:
                logging.error(f"Error processing {image_path.name}: {str(e)}")
                continue


async def main():
    # Configuration
    BASE_DIR = "/workspace/images"
    MODEL_PATH = "OpenGVLab/InternVL2-8B"
    VERSION = "001"

    captioner = InternVLCardArtCaptioner(
        base_dir=BASE_DIR,
        model_path=MODEL_PATH,
        version=VERSION
    )

    await captioner.process_images()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())