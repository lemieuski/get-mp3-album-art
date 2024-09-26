import os
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3
import json
from datetime import datetime

# Your Google Custom Search API key and Search Engine ID
GOOGLE_API_KEY = 'enter your api key'
SEARCH_ENGINE_ID = 'enter your search engine ID'
LIMIT_PER_DAY = 100

# File to store progress
PROGRESS_FILE = 'progress.json'

# Function to search for MP3 files in a directory and group by album
def find_mp3_files_by_album(directory):
    albums = {}
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".mp3"):
                mp3_file = os.path.join(root, file)
                artist, album = get_metadata(mp3_file)
                if artist and album:
                    # Group by artist and album
                    album_key = (artist, album)
                    if album_key not in albums:
                        albums[album_key] = []
                    albums[album_key].append(mp3_file)
    return albums

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

# Function to save the album cover as cover.jpg in the album directory
def save_image_as_cover(album_directory, image_data):
    if not image_data:
        return
    
    # Set the path for cover.jpg
    cover_path = os.path.join(album_directory, "cover.jpg")
    
    try:
        with open(cover_path, 'wb') as f:
            f.write(image_data)
        print(f"Album cover saved as {cover_path}")
    except Exception as e:
        print(f"Failed to save album cover in {cover_path}: {e}")

# Function to track progress across days
def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    else:
        return {'last_run': str(datetime.today().date()), 'albums_processed_today': 0}

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
        progress['albums_processed_today'] = 0

    albums = find_mp3_files_by_album(directory)
    
    for (artist, album), mp3_files in albums.items():
        if progress['albums_processed_today'] >= LIMIT_PER_DAY:
            print(f"Limit of {LIMIT_PER_DAY} albums reached for today. Stopping.")
            break

        # Get the album directory from the first MP3 file in the album
        album_directory = os.path.dirname(mp3_files[0])
        
        # Check if cover.jpg already exists in the album folder
        cover_path = os.path.join(album_directory, "cover.jpg")
        if os.path.exists(cover_path):
            print(f"Cover already exists for {album} by {artist} in {album_directory}")
            continue

        print(f"Processing album '{album}' by '{artist}'")

        # Search for the album cover
        image_url = search_album_cover(artist, album)
        if image_url:
            image_data = download_image(image_url)
            save_image_as_cover(album_directory, image_data)
            progress['albums_processed_today'] += 1
            save_progress(progress)
        else:
            print(f"No album cover found for {album} by {artist}")

if __name__ == "__main__":
    music_directory = "/path/to/your/music/directory"  # Set your music directory here
    main(music_directory)
