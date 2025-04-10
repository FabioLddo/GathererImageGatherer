#!/usr/bin/env python
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
import yaml
import urllib.request
import urllib.parse
import requests
import certifi
import os
import time
from concurrent.futures import ThreadPoolExecutor
import warnings

import urllib3
warnings.simplefilter('ignore', urllib3.exceptions.InsecureRequestWarning)

from write_captions import create_caption_for_card


def get_first_pic(url):
    """Fetches the first card from the page."""
    try:
        result = requests.get(url, verify=False)
        result.raise_for_status()
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
        return soup.find_all("span", "cardTitle")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching pics: {e}")
        return []

def download_pic(sample, set_name):
    """Gets the card name and multiverseID from a sample and saves the image."""
    try:
        expansion = f'data/images/{set_name.replace("%20", "_")}'
        os.makedirs(expansion, exist_ok=True)
        
        if not sample.a:
            return

        multiverse_id = sample.a.attrs['href'][34:]
        card_name = f"{expansion}/{multiverse_id}.jpg"
        if os.path.exists(card_name):
            return

        sample_name = sample.a.get_text().replace('/', '||')
        print(f"- {sample_name}")
        
        url = f"https://gatherer.wizards.com/Handlers/Image.ashx?multiverseid={multiverse_id}&type=card"
        response = requests.get(url, verify=False)
        
        if response.status_code == 200:
            with open(card_name, "wb") as f:
                f.write(response.content)
    except Exception as e:
        print(f"Error downloading {sample_name}: {e}")

def process_set(line):
    """Processes a single set, fetching images in parallel."""
    n = 0
    last_first_pic = ""
    quoted_line = urllib.parse.quote(line)
    
    while n < 5:
        url = f"https://gatherer.wizards.com/Pages/Search/Default.aspx?page={n}&set=[%22{quoted_line}%22]"
        first_pic = get_first_pic(url)
        
        if first_pic and first_pic != last_first_pic:
            print("\n-----------------------------------------------")
            print(f"Downloading images from {line}")
            print("-----------------------------------------------")
            samples = get_pics(url)
            
            with ThreadPoolExecutor() as executor:
                executor.map(lambda sample: download_pic(sample, quoted_line), samples)
        else:
            break
        
        last_first_pic = first_pic
        n += 1

def main():
    """Main function to scrape and download card images."""
    config_file = 'config/expansions.yaml' if os.path.exists('config/expansions.yaml') else 'config/cardSets.txt'
    os.makedirs('data/images', exist_ok=True)
    
    if config_file.endswith('.yaml'):
        with open(config_file, 'r') as sets:
            try:
                data = yaml.load(sets, Loader=yaml.FullLoader)
                expansions = data.get('expansions', [])
            except yaml.YAMLError as e:
                print(f"Error parsing YAML: {e}")
                return
    else:
        with open(config_file, 'r') as sets:
            expansions = [line.strip() for line in sets if line.strip() and not line.startswith('//')]
    
    with ThreadPoolExecutor() as executor:
        executor.map(process_set, expansions)

if __name__ == "__main__":
    main()
