import requests
import os
import json
import logging
import unicodedata

def clean_unicode(text: str) -> str:
    # Normalize Unicode to NFKD form and encode to ASCII
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def cut_caption(content):
    """Read a caption file, crop it up to the last period, and save it back."""
    try:        
        content = content.strip()
        
        # Find the last period in the text
        last_period_index = content.rfind('.')
        
        if last_period_index != -1:
            # Crop text up to the last period (including it)
            new_content = content[:last_period_index + 1]
            return new_content
            
        else:
            return False, f"No period found in: {content}"
    
    except Exception as e:
        return False, f"Error processing {content}: {str(e)}"



def save_metadata(multiverse_id, image_path):
    try:
        api_url = f"https://api.scryfall.com/cards/multiverse/{multiverse_id}?language=en"
        response = requests.get(api_url)
        
        # Check HTTP status code first
        if response.status_code == 404:
            logging.warning(f"Card not found for multiverse_id {multiverse_id}: 404 Not Found")
            return False

        data = response.json()
        
        # Check if the response contains an error
        if 'error' in data:
            error_code = data.get('code', 'unknown')
            error_details = data.get('details', 'No details provided')
            logging.error(f"Error fetching data for {multiverse_id}: {error_code} - {error_details}")
            return False
        
        # save the json data to a file
        json_path = os.path.splitext(image_path)[0] + ".json"
        with open(json_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4)

        # Generate the caption using the combined methodology, removed from the scraper, doing it later
        # caption = generate_caption(data)

        # if not caption:
        #     # logging.warning(f"Caption generation failed for {multiverse_id}.")
        #     return False

        # Save the caption to a text file
        # text_path = os.path.splitext(image_path)[0] + ".txt"
        # with open(text_path, "w", encoding="utf-8") as txt_file:
        #     txt_file.write(caption)

        return True
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error for {multiverse_id}: {e}")
        return False
    except Exception as e:
        logging.error(f"Error creating caption file for {multiverse_id}: {e}")
        return False
    

def generate_caption_from_metadata(card_data):
    """
    Args:
        card_data (dict): A dictionary representing the card's JSON data.

    Returns:
        str: A descriptive caption for the card.
    """

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
    caption = " ".join(description_parts)

    # convert all to utf-8
    caption = clean_unicode(caption)

    return caption


# Deprecated function, kept for reference
def create_caption_for_card(multiverse_id, image_path):
    try:
        api_url = f"https://api.scryfall.com/cards/multiverse/{multiverse_id}?language=en"
        response = requests.get(api_url)
        
        # Check HTTP status code first
        if response.status_code == 404:
            logging.warning(f"Card not found for multiverse_id {multiverse_id}: 404 Not Found")
            return False

        data = response.json()
        
        # Check if the response contains an error
        if 'error' in data:
            error_code = data.get('code', 'unknown')
            error_details = data.get('details', 'No details provided')
            logging.error(f"Error fetching data for {multiverse_id}: {error_code} - {error_details}")
            return False
        
        # save the json data to a file
        json_path = os.path.splitext(image_path)[0] + ".json"
        with open(json_path, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4)

        # Generate the caption using the combined methodology, removed from the scraper, doing it later
        # caption = generate_caption(data)

        # if not caption:
        #     # logging.warning(f"Caption generation failed for {multiverse_id}.")
        #     return False

        # Save the caption to a text file
        # text_path = os.path.splitext(image_path)[0] + ".txt"
        # with open(text_path, "w", encoding="utf-8") as txt_file:
        #     txt_file.write(caption)

        return True
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error for {multiverse_id}: {e}")
        return False
    except Exception as e:
        logging.error(f"Error creating caption file for {multiverse_id}: {e}")
        return False

# Deprecated function, kept for reference
def generate_caption(card_data):
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
    caption = " ".join(description_parts)

    # convert all to utf-8
    caption = caption.encode('utf-8', 'ignore').decode('utf-8').replace("\u2014", "-")

    return caption


# if __name__ == "__main__":
#     # Example usage
#     multiverse_id = "527289"
# https://api.scryfall.com/cards/multiverse/527289?language=en
# https://api.scryfall.com/cards/fc45c9d4-ecc7-4a9d-9efe-f4b7d697dd97?language=en
#     image_path = "./temp/temp_box_art_527289.png"
#     image_path = "data/images/Adventures_in_the_Forgotten_Realms/527289.jpg"
#     img = Image.open(image_path)
    
#     success = create_caption_for_card(multiverse_id, image_path, img)
#     if success:
#         print(f"Caption created successfully for {multiverse_id}.")
#     else:
#         print(f"Failed to create caption for {multiverse_id}.")