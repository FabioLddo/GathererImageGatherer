#!/usr/bin/env python3
import yaml
import urllib.parse
import os

def main():
    # ...existing code for other imports...
    expansions_file = os.path.join(os.path.dirname(__file__), '../config/expansions.yaml')
    card_sets_file = os.path.join(os.path.dirname(__file__), '../config/cardSets.txt')

    with open(expansions_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}
    expansions = data.get('expansions', [])

    encoded = set(urllib.parse.quote(e, safe='') for e in expansions)
    with open(card_sets_file, 'w', encoding='utf-8') as out:
        out.write('\n'.join(sorted(encoded)) + '\n')

if __name__ == '__main__':
    main()
