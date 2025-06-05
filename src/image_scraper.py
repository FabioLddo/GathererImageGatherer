import aiohttp
from aiohttp import ClientSession, ClientTimeout
from bs4 import BeautifulSoup, FeatureNotFound
from pathlib import Path
from PIL import Image, UnidentifiedImageError
import yaml
import urllib.parse
import logging
import ssl
from write_captions import save_metadata

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('image_scraping.log'),
        logging.StreamHandler()
    ]
)

# Constants
BASE_URL = "https://gatherer.wizards.com"
IMAGE_URL = BASE_URL + "/Handlers/Image.ashx?multiverseid={}&type=card"
DATA_DIR = Path("data/images")
CONFIG_PATH = Path("config/expansions.yaml")
TIMEOUT = ClientTimeout(total=30)
HEADERS = {"User-Agent": "Mozilla/5.0"}
MAX_RETRIES = 3


# Validate and save image
async def save_image(session: ClientSession, url: str, path: Path, multiverse_id: str):
    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    # path.write_bytes(content)
                    # Create a BytesIO object to handle the image in memory
                    from io import BytesIO
                    image_data = BytesIO(content)

                    # Validate image
                    try:
                        # with Image.open(path) as img:
                        #     img.verify()

                        # Open image from memory and convert to RGB to fix profile issues
                        with Image.open(image_data) as img:
                            # Convert to RGB (removes problematic color profiles)
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            # Save as JPG with good quality
                            img.save(path, 'JPEG')

                    except (UnidentifiedImageError, OSError) as e:
                        logging.warning(f"Corrupted image at {path.name}, removing.")
                        path.unlink()
                        if attempt < MAX_RETRIES - 1:
                            logging.warning(f"Retry {attempt+1} for {url} due to corrupted image: {e}")
                            continue
                        else:
                            logging.error(f"Corrupted image after {MAX_RETRIES} attempts: {e}")
                            return False

                    caption_created = save_metadata(multiverse_id, str(path))
                    
                    if not caption_created:
                        logging.error(f"Failed to create caption for {path.name}")
                        path.unlink()
                        return False
                    
                    logging.info(f"Downloaded: {path.name}")
                    return True
                else:
                    logging.error(f"Failed to fetch {url} — status {resp.status}")
                    return False
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logging.warning(f"Retry {attempt+1} for {url} due to: {e}")
                continue
            else:
                logging.error(f"Exception fetching {url} after {MAX_RETRIES} attempts: {e}")
                return False


# Parse one page of cards
async def get_cards_on_page(session: ClientSession, set_name: str, page: int):
    url = f"{BASE_URL}/Pages/Search/Default.aspx?page={page}&set=[%22{urllib.parse.quote(set_name)}%22]"
    try:
        async with session.get(url) as resp:
            if resp.status == 200:
                try:
                    soup = BeautifulSoup(await resp.text(), "lxml")
                except FeatureNotFound:
                    soup = BeautifulSoup(await resp.text(), "html.parser")
                return soup.find_all("span", class_="cardTitle")
    except Exception as e:
        logging.error(f"Error getting cards from {url}: {e}")
    return []


# Download all card images from one expansion
async def download_set(session: ClientSession, set_name: str):
    logging.info(f"Processing set: {set_name}")
    set_folder = DATA_DIR / set_name.replace(" ", "_")
    set_folder.mkdir(parents=True, exist_ok=True)

    seen_ids = set()
    for page in range(5):  # Check up to 5 pages per set
        card_spans = await get_cards_on_page(session, set_name, page)
        if not card_spans:
            break

        tasks = []
        for span in card_spans:
            link = span.find("a")
            if link:
                href = link["href"]
                multiverse_id = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("multiverseid", [None])[0]
                if multiverse_id and multiverse_id not in seen_ids:
                    seen_ids.add(multiverse_id)
                    img_path = set_folder / f"{multiverse_id}.jpg"
                    if not img_path.exists():
                        image_url = IMAGE_URL.format(multiverse_id)
                        tasks.append(save_image(session, image_url, img_path, multiverse_id))
        if tasks:
            await asyncio.gather(*tasks)

# Load sets from YAML config
def load_sets():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
            return config.get("expansions", [])
    logging.error("No configuration file found.")
    return []

# Main
async def main():
    sets = load_sets()
    # sets = sets[:5]  # Limit to first 5 sets for testing
    if not sets:
        return
    
    sslcontext = ssl.create_default_context()
    sslcontext.check_hostname = False
    sslcontext.verify_mode = ssl.CERT_NONE

    async with aiohttp.ClientSession(timeout=TIMEOUT, headers=HEADERS, connector=aiohttp.TCPConnector(ssl=sslcontext)) as session:
        for set_name in sets:
            await download_set(session, set_name)

    # async with aiohttp.ClientSession(timeout=TIMEOUT, headers=HEADERS) as session:
    #     for set_name in sets:
    #         await download_set(session, set_name)

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
