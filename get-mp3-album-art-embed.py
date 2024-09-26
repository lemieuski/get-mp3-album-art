import os
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
import json
from datetime import datetime

# Your Google Custom Search API key and Search Engine ID
GOOGLE_API_KEY = 'your_google_api_key'
SEARCH_ENGINE_ID = 'your_search_engine_id'
LIMIT_PER_DAY = 100

# File to store progress
PROGRESS_FILE = 'progress.json'

# Function to search for MP3 files in a directory
def find_mp3_files(directory):
    mp3_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".mp3"):
                mp3_files.append(os.path.join(root, file))
    return mp3_files

# Function to get metadata (artist and album) from the MP3 file
def get_metadata(mp3_file):
    audio = MP3(mp3_file, ID3=ID3)
    artist = audio['TPE1'].text[0] if 'TPE1' in audio else None
    album = audio['TALB'].text[0] if 'TALB' in audio else None
    return artist, album

# Function to search for album art on Google
def search_album_cover(artist, album):
    if not artist or not album:
        return None
    
    query = f"{artist} {album} album cover"
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&cx={SEARCH_ENGINE_ID}&key={GOOGLE_API_KEY}&searchType=image&num=1"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            items = response.json().get('items')
            if items:
                # Return the first image link
                return items[0]['link']
            else:
                print(f"No image results for {query}")
                return None
        else:
            print(f"Error fetching image: {response.status_code}, {response.text}")
            return None
    except requests.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return None

# Function to download the album art image
def download_image(image_url):
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            return response.content
        else:
            print(f"Failed to download image: {response.status_code}")
            return None
    except requests.RequestException as e:
        print(f"HTTP Request failed: {e}")
        return None

# Function to embed album art into the MP3 file
def embed_album_cover(mp3_file, image_data):
    if not image_data:
        return
    
    try:
        audio = MP3(mp3_file, ID3=ID3)
        audio.tags.add(
            APIC(
                encoding=3,  # 3 is for utf-8
                mime='image/jpeg',  # Image type
                type=3,  # 3 is for album art
                desc='Cover',
                data=image_data
            )
        )
        audio.save()
        print(f"Album cover embedded in {mp3_file}")
    except Exception as e:
        print(f"Failed to embed album cover in {mp3_file}: {e}")

# Function to track progress across days
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    else:
        return {'last_run': str(datetime.today().date()), 'files_processed_today': 0}

def save_progress(progress):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

# Main function
def main(directory):
    progress = load_progress()
    today = str(datetime.today().date())

    # Reset the count if it's a new day
    if progress['last_run'] != today:
        progress['last_run'] = today
        progress['files_processed_today'] = 0

    mp3_files = find_mp3_files(directory)
    
    for mp3_file in mp3_files:
        if progress['files_processed_today'] >= LIMIT_PER_DAY:
            print(f"Limit of {LIMIT_PER_DAY} files reached for today. Stopping.")
            break

        print(f"Processing {mp3_file}")
        artist, album = get_metadata(mp3_file)
        if artist and album:
            print(f"Found metadata - Artist: {artist}, Album: {album}")
            image_url = search_album_cover(artist, album)
            if image_url:
                image_data = download_image(image_url)
                embed_album_cover(mp3_file, image_data)
                progress['files_processed_today'] += 1
                save_progress(progress)
            else:
                print(f"No album cover found for {artist} - {album}")
        else:
            print(f"Metadata missing for {mp3_file}")

if __name__ == "__main__":
    music_directory = "/path/to/your/music/directory"  # Set your music directory here
    main(music_directory)
