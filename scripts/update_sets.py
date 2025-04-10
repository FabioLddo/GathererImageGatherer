import re
import sys
import os
import requests


# --- Configuration ---
# Input file containing the wiki table markup
# Make sure this file exists in the same directory as the script,
# or provide the full path.
INPUT_FILENAME = os.path.join(os.path.dirname(__file__), '../config/source_data.txt')

# Output file where the YAML data will be saved
OUTPUT_FILENAME = os.path.join(os.path.dirname(__file__), '../config/mtg_expansions.yaml')

# Regular expression to extract the set name
# It looks for text inside [[...]]
# It handles both [[Link]] and [[Link|Display Name]], extracting 'Link' or 'Display Name'
# It assumes the relevant part of the string looks like ''[[...]]'' or similar variations
# Breakdown:
# \[\[      : Matches the opening [[
# (?:       : Starts a non-capturing group (for the optional link part)
#   [^|\]]+ : Matches one or more characters that are NOT | or ] (the link target)
#   \|      : Matches the literal | separator
# )?        : Makes the entire non-capturing group optional (for cases without |)
# (         : Starts the capturing group (this is what we want to extract)
#   [^\]]+  : Matches one or more characters that are NOT ] (the display name or link)
# )         : Ends the capturing group
# \]\]      : Matches the closing ]]
SET_NAME_REGEX = re.compile(r"\[\[(?:[^|\]]+\|)?([^\]]+)\]\]")

# --- Main Script ---

def extract_set_names(input_file):
    """
    Reads the input file, extracts set names from wiki table rows,
    and returns a list of names.
    """
    extracted_names = []
    print(f"Reading from: {input_file}")
    try:
        with open(input_file, 'r', encoding='utf-8') as infile:
            for line in infile:
                # Check if it looks like a table data row
                if line.strip().startswith('| '):
                    columns = line.split('||')
                    # Ensure there are enough columns (Date, Set, Symbol, etc.)
                    # The set name is expected in the second column (index 1)
                    if len(columns) > 1:
                        set_column_text = columns[1].strip()

                        # Search for the pattern [[...]] within the column text
                        match = SET_NAME_REGEX.search(set_column_text)
                        if match:
                            # Extract the captured group (the set name)
                            set_name = match.group(1).strip()
                            if set_name: # Ensure we extracted something
                                print(f"  Found: {set_name}")
                                extracted_names.append(set_name)
                        # else:
                            # Optional: print lines where the pattern wasn't found for debugging
                            # print(f"  Pattern not found in: {set_column_text}")

    except FileNotFoundError:
        print(f"Error: Input file '{input_file}' not found.", file=sys.stderr)
        return None # Indicate failure
    except Exception as e:
        print(f"An error occurred while reading the file: {e}", file=sys.stderr)
        return None # Indicate failure

    print(f"Total names extracted: {len(extracted_names)}")
    return extracted_names

def write_yaml_output(output_file, names):
    """
    Writes the list of names to the specified output file in YAML format.
    """
    if names is None:
        print("Skipping YAML output due to previous errors.")
        return

    print(f"Writing to: {output_file}")
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            outfile.write("expansions:\n") # Write the header
            for name in names:
                # Write each name, indented and quoted
                outfile.write(f'    - "{name}"\n')
        print("Successfully wrote YAML file.")
    except Exception as e:
        print(f"An error occurred while writing the YAML file: {e}", file=sys.stderr)


def get_set_names():
    """
    Fetches the MTG set names from the Gatherer website.
    This function is a placeholder and doesn't currently extract data.
    """

    url = 'https://gatherer.wizards.com/Pages/Default.aspx'
    response = requests.get(url, verify=False)  # Disable SSL verification
    html_content = response.text

    print("Response Status Code:", response.status_code)
    print(html_content)

    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, 'html.parser')
    set_dropdown = soup.find('select', {'name': 'ctl00$ctl00$MainContent$Content$SearchControls$setAddText'})
    set_options = set_dropdown.find_all('option')
    sets = [option.text.strip() for option in set_options if option.text.strip()]
    print("Sets found:", len(sets))
    return sets


# --- Execution ---
if __name__ == "__main__":
    print("Starting MTG Set Name Extraction...")
    # set_names = extract_set_names(INPUT_FILENAME)
    set_names = get_set_names()
    write_yaml_output(OUTPUT_FILENAME, set_names)
    print("Script finished.")

