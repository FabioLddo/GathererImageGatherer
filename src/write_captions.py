import requests
import os

def create_caption_for_card(multiverse_id, image_path):
    try:
        api_url = f"https://api.scryfall.com/cards/multiverse/{multiverse_id}?language=en"
        response = requests.get(api_url)
        data = response.json()

        # Generate the caption using the combined methodology
        caption = generate_caption(data)
        text_path = os.path.splitext(image_path)[0] + ".txt"
        with open(text_path, "w", encoding="utf-8") as txt_file:
            txt_file.write(caption)
    except Exception as e:
        print(f"Error creating caption file for {multiverse_id}: {e}")


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

    return caption