import pandas as pd
import os
import argparse

def parse_args():
    parser = argparse.ArgumentParser(description="Convert parquet captions to text files")
    parser.add_argument("--parquet_file", type=str, required=True, help="Path to the parquet file")
    parser.add_argument("--output_dir", type=str, required=True, help="Directory to save caption text files")
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Read the parquet file
    df = pd.read_parquet(args.parquet_file)
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # For each row in the dataframe
    for _, row in df.iterrows():
        filename = row['filename']
        caption = row['caption']
        
        # Get the base filename without extension
        base_name = os.path.splitext(filename)[0]
        
        # Create the text file path
        text_file_path = os.path.join(args.output_dir, f"{base_name}.txt")
        
        # Write the caption to the text file
        with open(text_file_path, 'w') as f:
            f.write(caption)
        
        print(f"Created caption file: {text_file_path}")

if __name__ == "__main__":
    main()

#     python toolkit/captioning/parquet_to_textfiles.py \
#   --parquet_file captions_output.[folder_name].parquet \
#   --output_dir /path/to/save/text/files