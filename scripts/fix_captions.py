import os
import argparse
import glob


def fix_caption(file_path):
    """Read a caption file, crop it up to the last period, and save it back."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        # Find the last period in the text
        last_period_index = content.rfind('.')
        
        if last_period_index != -1:
            # Crop text up to the last period (including it)
            new_content = content[:last_period_index + 1]
            
            # Save the updated content back to the file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True, f"Fixed: {os.path.basename(file_path)}"
        else:
            return False, f"No period found in: {os.path.basename(file_path)}"
    
    except Exception as e:
        return False, f"Error processing {os.path.basename(file_path)}: {str(e)}"


def process_directory(directory):
    """Process all .txt files in the given directory."""
    success_count = 0
    error_count = 0
    caption_files = []
    
    # Walk through directory and all subdirectories
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.txt'):
                caption_files.append(os.path.join(root, file))
    
    print(f"Found {len(caption_files)} caption files across all subdirectories.")
    
    
    for file_path in caption_files:
        success, message = fix_caption(file_path)
        print(message)
        if success:
            success_count += 1
        else:
            error_count += 1
    
    print(f"\nSummary: {success_count} files fixed, {error_count} files with errors or no periods.")


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(description="Fix caption files by cropping text up to the last period.")
#     parser.add_argument("dir", nargs='?', default=".", help="Directory containing the caption files (default: current directory)")
    
#     args = parser.parse_args()
#     process_directory(args.dir)


# TODO i should add this process to the captioners, as a check, so that it is done automatically when captions are generated - DONE
# TODO also it might be better to resize all images to a fixed size, so that they are all the same size OR use the scryfall images and caption them, since it is so "easy" - SHOULDN'T BE NEEDED
