#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import yaml
import urllib.request
import urllib.parse
import requests
import certifi
import warnings
import urllib3
import concurrent.futures
warnings.simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)

import os
import time

from write_captions import create_caption_for_card

def get_first_pic(url):
    """Fetches the first card from the page."""
    try:
        result = requests.get(url, verify=False)
        result.raise_for_status()  # Raise exception for HTTP errors
        soup = BeautifulSoup(result.content, "lxml")
        hold = soup.find("span", "cardTitle")
        if hold and hold.a:
            return hold.a.get_text()
        return ""
    except requests.exceptions.RequestException as e:
        print(f"Error fetching first pic: {e}")
        return ""


def get_pics(url):
    """Generates a list of xml samples of card titles."""
    try:
        result = requests.get(url, verify=False)
        result.raise_for_status()
        soup = BeautifulSoup(result.content, "lxml")
        samples = soup.find_all("span", "cardTitle")
        return samples
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pics: {e}")
        return []


def download_pic(i, samples, set_name):
    """Gets the card name and multiverseID's from a sample and then saves them."""
    try:
        expansion = 'data/images/' + set_name.replace('%20', '_')

        if not os.path.exists(expansion):
            os.makedirs(expansion)
        else:
            # Skip if the card image already exists
            multiverse_id = samples[i].a.attrs['href']
            multiverse_id = multiverse_id[34:]
            card_name = f"{expansion}/{multiverse_id}.jpg"
            if os.path.exists(card_name):
                print(f"Already downloaded: {card_name}", flush=True)
                return

        if i >= len(samples) or not samples[i].a:
            return

        multiverse_id = samples[i].a.attrs['href']
        multiverse_id = multiverse_id[34:]

        sample_name = samples[i].a.get_text()
        sample_name = sample_name.replace('/', '||')

        print(f"- {sample_name}", flush=True)

        card_name = f"{expansion}/{multiverse_id}.jpg"
        url = f"https://gatherer.wizards.com/Handlers/Image.ashx?multiverseid={multiverse_id}&type=card"

        if not os.path.exists(card_name):
            response = requests.get(url, verify=False)  # Disable SSL verification

            if response.status_code == 200:
                with open(card_name, "wb") as f:
                    f.write(response.content)

                create_caption_for_card(multiverse_id, card_name)
                
                time.sleep(0.1)  # Avoid hammering the server

    except Exception as e:
        print(f"Error downloading {sample_name}: {e}")


def main():
    """Main function to scrape and download card images."""
    # Check if YAML exists, otherwise fall back to txt
    config_file = 'config/expansions.yaml'
    if not os.path.exists(config_file):
        config_file = 'config/cardSets.txt'
        
    # Create output directory if it doesn't exist
    if not os.path.exists('data/images'):
        os.makedirs('data/images')
    
    samples = []
    last_first_pic = ""
    
    # Process the configuration file based on its type
    if config_file.endswith('.yaml'):
        with open(config_file, 'r') as sets:
            try:
                data = yaml.load(sets, Loader=yaml.FullLoader)
                expansions = data.get('expansions', [])
            except yaml.YAMLError as e:
                print(f"Error parsing YAML: {e}")
                return
    else:
        # Process old text format
        with open(config_file, 'r') as sets:
            expansions = [line.strip() for line in sets if line.strip() and not line.startswith('//')]
    
    for line in expansions:
        n = 0
        # Hardcoded based on biggest set 'Fifth Edition' with 449 cards
        # We'll check up to 5 pages for each set
        while n < 5:
            # This loops through the different pages page=0, page=1 etc.
            quoted_line = urllib.parse.quote(line)
            url = f"https://gatherer.wizards.com/Pages/Search/Default.aspx?page={n}&set=[%22{quoted_line}%22]"

            # Check if the first pic is the same as the last first pic
            first_pic = get_first_pic(url)
            if first_pic and first_pic != last_first_pic:
                print("\n-----------------------------------------------")
                print(f"Downloading images from {line}")
                print("-----------------------------------------------")
                samples = get_pics(url)
                with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                    for p in range(len(samples)):
                        executor.submit(download_pic, p, samples, quoted_line)
            else:
                # Exit the loop if we've reached the end of unique pages
                break
                
            last_first_pic = first_pic
            n += 1


if __name__ == "__main__":
    main()
