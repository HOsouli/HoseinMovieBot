
import os
import re
import time
import requests
from urllib.parse import quote
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor


load_dotenv()

TMDB_TOKEN = os.getenv("TMDB_TOKEN")

MOVIE_CACHE = {}
CACHE_DURATION = 1800

def detect_quality(filename, file_info=None):
    if file_info:
        try:
            height = int(file_info.get('height', 0) or 0)
            if height >= 2000:
                return '2160p'
            if height >= 1300:
                return '1440p'
            if height >= 1000:
                return '1080p'
            if height >= 700:
                return '720p'
            if height >= 450:
                return '480p'
            if height >= 300:
                return '360p'
            if height >= 200:
                return '240p'
        except (TypeError, ValueError):
            pass
    name = filename.lower()
    patterns = [
        (r'\b2160p\b|\b4k\b|\buhd\b', '2160p'),
        (r'\b1440p\b|\b2k\b', '1440p'),
        (r'\b1080p\b|full[\s._-]?hd', '1080p'),
        (r'\b720p\b', '720p'),
        (r'\b480p\b', '480p'),
        (r'\b360p\b', '360p'),
        (r'\b240p\b', '240p'),
    ]
    for pattern, quality in patterns:
        if re.search(pattern, name):
            return quality
    return 'نامشخص'

def detect_language(filename):
    name = filename.lower()
    if any(word in name for word in ['persian', 'farsi', 'dubbed', 'dubbing', 'دوبله', 'فارسی']):
        return 'دوبله فارسی'
    if any(word in name for word in ['english', 'original', 'زبان اصلی']):
        return 'زبان اصلی'
    return 'نامشخص'

def detect_subtitle_language(filename):
    name = filename.lower()
    if any(word in name for word in ['persian', 'farsi', 'فارسی', 'fa.srt']):
        return 'زیرنویس فارسی'
    if any(word in name for word in ['english', 'eng.srt', 'en.srt']):
        return 'زیرنویس انگلیسی'
    return 'زیرنویس با زبان نامشخص'

def get_item_versions(item, movie_title, release_year):
    identifier = item['identifier']
    try:
        response = requests.get(f"https://archive.org/metadata/{identifier}", timeout=15)
        response.raise_for_status()
        metadata = response.json()
        info = metadata.get('metadata', {})
        archive_year = str(info.get('year', ''))

        if release_year and archive_year and release_year != archive_year:
            return []
        rights = str(info.get('rights', '')).lower()
        license_url = str(info.get('licenseurl', '')).lower()
        is_public_domain = (
            'public domain' in rights
            or 'creativecommons.org/publicdomain/mark/1.0/' in license_url
            or 'creativecommons.org/publicdomain/zero/1.0/' in license_url
        )
        if not is_public_domain:
            return []
        files = metadata.get('files', [])
        subtitle_files = []
        for file in files:
            filename = file.get('name', '')
            if filename.lower().endswith(('.srt', '.vtt', '.ass', '.ssa')):
                subtitle_files.append({
                    'language': detect_subtitle_language(filename),
                    'filename': filename,
                    'url': f"https://archive.org/download/{identifier}/{quote(filename, safe='/')}"
                })
        versions = []
        for file in files:
            filename = file.get('name', '')

            if not filename.lower().endswith(('.mp4', '.ogv', '.mkv', '.webm')):
                continue

            print(
                "VIDEO META:",
                filename,
                {
                    key: file.get(key)
                    for key in ('width', 'height', 'length', 'size', 'format')
                }
            )

            size = int(file.get('size', 0) or 0)
            if not filename.lower().endswith(('.mp4', '.ogv', '.mkv', '.webm')):
                continue
            if file.get('private') or not 0 < size <= 5 * 1024 * 1024 * 1024:
                continue
            versions.append({
                'title': item.get('title', movie_title),
                'quality': detect_quality(filename, file),
                'language': detect_language(filename),
                'subtitles': subtitle_files,
                'identifier': identifier,
                'filename': filename,
                'download_url': f"https://archive.org/download/{identifier}/{quote(filename, safe='/')}",
                'stream_url': f"https://archive.org/embed/{identifier}"
            })
        return versions
    except (requests.exceptions.RequestException, ValueError, KeyError) as error:
        print(f"Metadata error ({identifier}): {error}")
        return []

def get_movie_versions(movie_id):
    cached = MOVIE_CACHE.get(str(movie_id))
    MOVIE_CACHE.clear()
    if cached and time.time() - cached['time'] < CACHE_DURATION:
        print("Movie versions loaded from cache")
        return cached['versions']
    headers = {
        'Authorization': f'Bearer {TMDB_TOKEN}',
        'accept': 'application/json'
    }
    try:
        movie_response = requests.get(
            f"https://api.themoviedb.org/3/movie/{movie_id}",
            headers=headers,
            params={'language': 'en-US'},
            timeout=10
        )
        movie_response.raise_for_status()
        movie = movie_response.json()
        movie_title = movie.get('title') or movie.get('original_title')
        release_date = movie.get('release_date', '')
        release_year = release_date[:4] if release_date else None
        query = (
            f'title:"{movie_title}" AND year:{release_year} AND mediatype:movies'
            if release_year else f'title:"{movie_title}" AND mediatype:movies'
        )
        search_response = requests.get(
            'https://archive.org/advancedsearch.php',
            params={
                'q': query,
                'fl[]': ['identifier', 'title'],
                'rows': 20,
                'output': 'json'
            },
            timeout=15
        )
        search_response.raise_for_status()
        results = search_response.json()['response']['docs']
        matching_items = []
        for item in results:
            archive_title = item.get('title', '').strip().lower()
            normalized_title = movie_title.strip().lower()
            if archive_title == normalized_title or archive_title.startswith(normalized_title + ' ('):
                matching_items.append(item)
        versions = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = executor.map(lambda item: get_item_versions(item, movie_title, release_year), matching_items)
            for item_versions in results:
                versions.extend(item_versions)
        print(f"Found versions: {len(versions)}")
        MOVIE_CACHE[str(movie_id)] = {
            'time': time.time(),
            'versions': versions
        }
        return versions
    except (requests.exceptions.RequestException, ValueError, KeyError) as error:
        print(f"Movie source error: {error}")
        return None
