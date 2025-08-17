#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Music Cache Scanner: Scans the cache/music directory for music files, extracts metadata, and generates a local playlist.

Dependency installation: pip install mutagen
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

try:
    from mutagen import File as MutagenFile
    from mutagen.id3 import ID3NoHeaderError
except ImportError:
    print("Error: The mutagen library needs to be installed")
    print("Please run: pip install mutagen")
    sys.exit(1)

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


class MusicMetadata:
    """
    Music metadata class.
    """

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.filename = file_path.name
        self.file_id = file_path.stem  # Filename without extension, i.e., the song ID
        self.file_size = file_path.stat().st_size
        self.creation_time = datetime.fromtimestamp(file_path.stat().st_ctime)
        self.modification_time = datetime.fromtimestamp(file_path.stat().st_mtime)

        # Metadata extracted from the file
        self.title = None
        self.artist = None
        self.album = None
        self.genre = None
        self.year = None
        self.duration = None  # in seconds
        self.bitrate = None
        self.sample_rate = None

        # File hash (for deduplication)
        self.file_hash = self._calculate_hash()

    def _calculate_hash(self) -> str:
        """
        Calculate the MD5 hash of the file (only the first 1MB to avoid slow computation for large files)
        """
        try:
            hash_md5 = hashlib.md5()
            with open(self.file_path, "rb") as f:
                # Read only the first 1MB to calculate the hash
                chunk = f.read(1024 * 1024)
                hash_md5.update(chunk)
            return hash_md5.hexdigest()[:16]  # Take the first 16 characters
        except Exception:
            return "unknown"

    def extract_metadata(self) -> bool:
        """
        Extract music file metadata.
        """
        try:
            audio_file = MutagenFile(self.file_path)
            if audio_file is None:
                return False

            # Basic information
            if hasattr(audio_file, "info"):
                self.duration = getattr(audio_file.info, "length", None)
                self.bitrate = getattr(audio_file.info, "bitrate", None)
                self.sample_rate = getattr(audio_file.info, "sample_rate", None)

            # ID3 tag information
            tags = audio_file.tags if audio_file.tags else {}

            # Title
            self.title = self._get_tag_value(tags, ["TIT2", "TITLE", "\xa9nam"])

            # Artist
            self.artist = self._get_tag_value(tags, ["TPE1", "ARTIST", "\xa9ART"])

            # Album
            self.album = self._get_tag_value(tags, ["TALB", "ALBUM", "\xa9alb"])

            # Genre
            self.genre = self._get_tag_value(tags, ["TCON", "GENRE", "\xa9gen"])

            # Year
            year_raw = self._get_tag_value(tags, ["TDRC", "DATE", "YEAR", "\xa9day"])
            if year_raw:
                # Extract the year number
                year_str = str(year_raw)
                if year_str.isdigit():
                    self.year = int(year_str)
                else:
                    # Try to extract the year from a date string
                    import re

                    year_match = re.search(r"(\d{4})", year_str)
                    if year_match:
                        self.year = int(year_match.group(1))

            return True

        except ID3NoHeaderError:
            # No ID3 tags, not an error
            return True
        except Exception as e:
            print(f"Failed to extract metadata for {self.filename}: {e}")
            return False

    def _get_tag_value(self, tags: dict, tag_names: List[str]) -> Optional[str]:
        """
        Get a value from multiple possible tag names.
        """
        for tag_name in tag_names:
            if tag_name in tags:
                value = tags[tag_name]
                if isinstance(value, list) and value:
                    return str(value[0])
                elif value:
                    return str(value)
        return None

    def format_duration(self) -> str:
        """
        Format the playback duration.
        """
        if self.duration is None:
            return "Unknown"

        minutes = int(self.duration) // 60
        seconds = int(self.duration) % 60
        return f"{minutes:02d}:{seconds:02d}"

    def format_file_size(self) -> str:
        """
        Format the file size.
        """
        size = self.file_size
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def to_dict(self) -> Dict:
        """
        Convert to dictionary format.
        """
        return {
            "file_id": self.file_id,
            "filename": self.filename,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "genre": self.genre,
            "year": self.year,
            "duration": self.duration,
            "duration_formatted": self.format_duration(),
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "file_size": self.file_size,
            "file_size_formatted": self.format_file_size(),
            "file_hash": self.file_hash,
            "creation_time": self.creation_time.isoformat(),
            "modification_time": self.modification_time.isoformat(),
        }


class MusicCacheScanner:
    """
    Music cache scanner.
    """

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or PROJECT_ROOT / "cache" / "music"
        self.playlist: List[MusicMetadata] = []
        self.scan_stats = {
            "total_files": 0,
            "success_count": 0,
            "error_count": 0,
            "total_duration": 0,
            "total_size": 0,
        }

    def scan_cache(self) -> bool:
        """
        Scan the cache directory.
        """
        print(f"🎵 Starting to scan music cache directory: {self.cache_dir}")

        if not self.cache_dir.exists():
            print(f"❌ Cache directory does not exist: {self.cache_dir}")
            return False

        # Find all music files
        music_files = []
        for pattern in ["*.mp3", "*.m4a", "*.flac", "*.wav", "*.ogg"]:
            music_files.extend(self.cache_dir.glob(pattern))

        if not music_files:
            print("📁 No music files found in the cache directory")
            return False

        self.scan_stats["total_files"] = len(music_files)
        print(f"📊 Found {len(music_files)} music files")

        # Scan each file
        for i, file_path in enumerate(music_files, 1):
            print(f"🔍 [{i}/{len(music_files)}] Scanning: {file_path.name}")

            try:
                metadata = MusicMetadata(file_path)

                if metadata.extract_metadata():
                    self.playlist.append(metadata)
                    self.scan_stats["success_count"] += 1

                    # Accumulate statistics
                    if metadata.duration:
                        self.scan_stats["total_duration"] += metadata.duration
                    self.scan_stats["total_size"] += metadata.file_size

                    # Display basic information
                    display_title = metadata.title or "Unknown Title"
                    display_artist = metadata.artist or "Unknown Artist"
                    print(
                        f"   ✅ {display_title} - {display_artist} ({metadata.format_duration()})"
                    )
                else:
                    self.scan_stats["error_count"] += 1
                    print(f"   ❌ Metadata extraction failed")

            except Exception as e:
                self.scan_stats["error_count"] += 1
                print(f"   ❌ Processing failed: {e}")

        return True

    def remove_duplicates(self):
        """
        Remove duplicate music files (based on hash value)
        """
        seen_hashes = set()
        unique_playlist = []
        duplicates = []

        for metadata in self.playlist:
            if metadata.file_hash in seen_hashes:
                duplicates.append(metadata)
            else:
                seen_hashes.add(metadata.file_hash)
                unique_playlist.append(metadata)

        if duplicates:
            print(f"🔄 Found {len(duplicates)} duplicate files:")
            for dup in duplicates:
                print(f"   - {dup.filename}")

        self.playlist = unique_playlist

    def sort_playlist(self, sort_by: str = "artist"):
        """
        Sort the playlist.
        """
        sort_functions = {
            "artist": lambda x: (
                x.artist or "Unknown",
                x.album or "Unknown",
                x.title or "Unknown",
            ),
            "title": lambda x: x.title or "Unknown",
            "album": lambda x: (x.album or "Unknown", x.artist or "Unknown"),
            "duration": lambda x: x.duration or 0,
            "file_size": lambda x: x.file_size,
            "creation_time": lambda x: x.creation_time,
        }

        if sort_by in sort_functions:
            self.playlist.sort(key=sort_functions[sort_by])
            print(f"📋 Playlist sorted by {sort_by}")

    def print_statistics(self):
        """
        Print scan statistics.
        """
        stats = self.scan_stats
        print(f"\n📊 Scan Statistics:")
        print(f"   Total files: {stats['total_files']}")
        print(f"   Successfully processed: {stats['success_count']}")
        print(f"   Failed to process: {stats['error_count']}")
        print(f"   Success rate: {stats['success_count']/stats['total_files']*100:.1f}%")

        # Total duration
        total_hours = stats["total_duration"] // 3600
        total_minutes = (stats["total_duration"] % 3600) // 60
        print(f"   Total playback duration: {total_hours} hours {total_minutes} minutes")

        # Total size
        total_size_mb = stats["total_size"] / (1024 * 1024)
        print(f"   Total file size: {total_size_mb:.1f} MB")

        # Average information
        if stats["success_count"] > 0:
            avg_duration = stats["total_duration"] / stats["success_count"]
            avg_size = stats["total_size"] / stats["success_count"]
            print(f"   Average duration: {int(avg_duration//60)}:{int(avg_duration%60):02d}")
            print(f"   Average size: {avg_size/(1024*1024):.1f} MB")

    def print_playlist(self, limit: int = None):
        """
        Print the playlist.
        """
        print(f"\n🎵 Local Music Playlist (Total {len(self.playlist)} songs)")
        print("=" * 80)

        for i, metadata in enumerate(
            self.playlist[:limit] if limit else self.playlist, 1
        ):
            title = metadata.title or "Unknown Title"
            artist = metadata.artist or "Unknown Artist"
            album = metadata.album or "Unknown Album"
            duration = metadata.format_duration()

            print(f"{i:3d}. {title}")
            print(f"     Artist: {artist}")
            print(f"     Album: {album}")
            print(f"     Duration: {duration} | File ID: {metadata.file_id}")
            print()

        if limit and len(self.playlist) > limit:
            print(f"... and {len(self.playlist) - limit} more songs")

    def export_playlist(self, output_file: Path = None, format: str = "json"):
        """
        Export the playlist.
        """
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = PROJECT_ROOT / f"local_playlist_{timestamp}.{format}"

        try:
            if format == "json":
                playlist_data = {
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "cache_directory": str(self.cache_dir),
                        "total_songs": len(self.playlist),
                        "statistics": self.scan_stats,
                    },
                    "playlist": [metadata.to_dict() for metadata in self.playlist],
                }

                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(playlist_data, f, ensure_ascii=False, indent=2)

            elif format == "m3u":
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("#EXTM3U\n")
                    for metadata in self.playlist:
                        title = metadata.title or metadata.filename
                        artist = metadata.artist or "Unknown Artist"
                        duration = int(metadata.duration) if metadata.duration else -1

                        f.write(f"#EXTINF:{duration},{artist} - {title}\n")
                        f.write(f"{metadata.file_path}\n")

            print(f"📄 Playlist exported to: {output_file}")
            return output_file

        except Exception as e:
            print(f"❌ Export failed: {e}")
            return None

    def search_songs(self, query: str) -> List[MusicMetadata]:
        """
        Search for songs.
        """
        query = query.lower()
        results = []

        for metadata in self.playlist:
            # Search in title, artist, album
            searchable_text = " ".join(
                filter(
                    None,
                    [
                        metadata.title,
                        metadata.artist,
                        metadata.album,
                        metadata.filename,
                    ],
                )
            ).lower()

            if query in searchable_text:
                results.append(metadata)

        return results

    def get_artists(self) -> Dict[str, List[MusicMetadata]]:
        """
        Group by artist.
        """
        artists = {}
        for metadata in self.playlist:
            artist = metadata.artist or "Unknown Artist"
            if artist not in artists:
                artists[artist] = []
            artists[artist].append(metadata)
        return artists

    def get_albums(self) -> Dict[str, List[MusicMetadata]]:
        """
        Group by album.
        """
        albums = {}
        for metadata in self.playlist:
            album_key = (
                f"{metadata.album or 'Unknown Album'} - {metadata.artist or 'Unknown Artist'}"
            )
            if album_key not in albums:
                albums[album_key] = []
            albums[album_key].append(metadata)
        return albums


def main():
    """
    Main function.
    """
    print("🎵 Music Cache Scanner")
    print("=" * 50)

    # Create a scanner
    scanner = MusicCacheScanner()

    # Scan the cache
    if not scanner.scan_cache():
        return

    # Remove duplicates
    scanner.remove_duplicates()

    # Sort the playlist
    scanner.sort_playlist("artist")

    # Show statistics
    scanner.print_statistics()

    # Show the playlist (limited to the first 20 songs)
    scanner.print_playlist(limit=20)

    # Interactive menu
    while True:
        print("\n" + "=" * 50)
        print("Select an action:")
        print("1. Show full playlist")
        print("2. Show grouped by artist")
        print("3. Show grouped by album")
        print("4. Search for songs")
        print("5. Export playlist (JSON)")
        print("6. Export playlist (M3U)")
        print("7. Re-sort")
        print("0. Exit")

        choice = input("\nPlease choose (0-7): ").strip()

        if choice == "0":
            break
        elif choice == "1":
            scanner.print_playlist()
        elif choice == "2":
            artists = scanner.get_artists()
            for artist, songs in artists.items():
                print(f"\n🎤 {artist} ({len(songs)} songs)")
                for song in songs:
                    title = song.title or song.filename
                    print(f"   - {title} ({song.format_duration()})")
        elif choice == "3":
            albums = scanner.get_albums()
            for album, songs in albums.items():
                print(f"\n💿 {album} ({len(songs)} songs)")
                for song in songs:
                    title = song.title or song.filename
                    print(f"   - {title} ({song.format_duration()})")
        elif choice == "4":
            query = input("Please enter search keywords: ").strip()
            if query:
                results = scanner.search_songs(query)
                if results:
                    print(f"\n🔍 Found {len(results)} songs:")
                    for i, song in enumerate(results, 1):
                        title = song.title or song.filename
                        artist = song.artist or "Unknown Artist"
                        print(f"   {i}. {title} - {artist} ({song.format_duration()})")
                else:
                    print("🔍 No matching songs found")
        elif choice == "5":
            scanner.export_playlist(format="json")
        elif choice == "6":
            scanner.export_playlist(format="m3u")
        elif choice == "7":
            print("Sort options:")
            print("1. By artist")
            print("2. By title")
            print("3. By album")
            print("4. By duration")
            print("5. By file size")
            print("6. By creation time")

            sort_choice = input("Please choose a sorting method (1-6): ").strip()
            sort_map = {
                "1": "artist",
                "2": "title",
                "3": "album",
                "4": "duration",
                "5": "file_size",
                "6": "creation_time",
            }

            if sort_choice in sort_map:
                scanner.sort_playlist(sort_map[sort_choice])
                print("✅ Sorting complete")
        else:
            print("❌ Invalid choice")

    print("\n👋 Goodbye!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 User interrupted, exiting program")
    except Exception as e:
        print(f"\n❌ Program exception: {e}")
        import traceback

        traceback.print_exc()
