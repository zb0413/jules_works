import asyncio
import os
import hashlib
import json
from enum import Enum

import aiofiles
import aiofiles.os as aios

class FileType(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    IMAGE = "image"
    UNKNOWN = "unknown"

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.aac', '.flac', '.ogg'}
TEXT_EXTENSIONS = {'.txt', '.md', '.json', '.xml', '.html', '.css', '.js', '.py', '.java', '.c', '.cpp'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}

async def scan_folder_files_info(folder_path: str) -> list[dict]:
    """
    Scans a folder for files and returns their name, path, and type.

    Args:
        folder_path: The path to the folder to scan.

    Returns:
        A list of dictionaries, where each dictionary contains:
        - name: The name of the file.
        - path: The absolute path to the file.
        - type: The determined FileType (VIDEO, AUDIO, TEXT, IMAGE, UNKNOWN).
    """
    files_info = []
    if not await aios.path.isdir(folder_path):
        raise ValueError(f"Provided path '{folder_path}' is not a directory or does not exist.")

    for entry in await aios.listdir(folder_path):
        entry_path = os.path.join(folder_path, entry)
        if await aios.path.isfile(entry_path):
            _, ext = os.path.splitext(entry.lower())
            file_type = FileType.UNKNOWN
            if ext in VIDEO_EXTENSIONS:
                file_type = FileType.VIDEO
            elif ext in AUDIO_EXTENSIONS:
                file_type = FileType.AUDIO
            elif ext in TEXT_EXTENSIONS:
                file_type = FileType.TEXT
            elif ext in IMAGE_EXTENSIONS:
                file_type = FileType.IMAGE

            files_info.append({
                "name": entry,
                "path": os.path.abspath(entry_path),
                "type": file_type.value
            })
    return files_info

async def scan_folder_contents(folder_path: str) -> list[dict]:
    """
    Scans a folder for files and directories, returning their name, path, and type (file/directory).

    Args:
        folder_path: The path to the folder to scan.

    Returns:
        A list of dictionaries, where each dictionary contains:
        - name: The name of the entry.
        - path: The absolute path to the entry.
        - type: "file" or "directory".
    """
    contents_info = []
    if not await aios.path.isdir(folder_path):
        raise ValueError(f"Provided path '{folder_path}' is not a directory or does not exist.")

    for entry in await aios.listdir(folder_path):
        entry_path = os.path.join(folder_path, entry)
        entry_type = "unknown"
        if await aios.path.isfile(entry_path):
            entry_type = "file"
        elif await aios.path.isdir(entry_path):
            entry_type = "directory"

        if entry_type in ["file", "directory"]: # Ensure we only add actual files/dirs
            contents_info.append({
                "name": entry,
                "path": os.path.abspath(entry_path),
                "type": entry_type
            })
    return contents_info

async def generate_md5_async(file_path: str, chunk_size: int = 8192) -> str | None:
    """
    Generates the MD5 checksum for a file asynchronously.

    Args:
        file_path: The path to the file.
        chunk_size: The size of chunks to read from the file.

    Returns:
        The MD5 checksum as a hex string, or None if the file doesn't exist.
    """
    if not await aios.path.isfile(file_path):
        return None

    md5_hash = hashlib.md5()
    async with aiofiles.open(file_path, 'rb') as f:
        while True:
            chunk = await f.read(chunk_size)
            if not chunk:
                break
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

async def _is_ffprobe_available():
    """Checks if ffprobe is available in PATH."""
    process = await asyncio.create_subprocess_shell(
        "ffprobe -version",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    return process.returncode == 0

async def extract_video_info_async(video_path: str) -> dict | None:
    """
    Extracts video file information using ffprobe.

    Args:
        video_path: The path to the video file.

    Returns:
        A dictionary containing video stream information, or None if an error occurs
        or the file is not a valid video.
        Raises FileNotFoundError if ffprobe is not installed/found.
    """
    if not await _is_ffprobe_available():
        raise FileNotFoundError("ffprobe command not found. Please install ffmpeg.")

    if not await aios.path.isfile(video_path):
        # print(f"Error: Video file '{video_path}' not found.")
        return None

    command = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        # print(f"Error executing ffprobe: {stderr.decode()}")
        return None

    try:
        data = json.loads(stdout.decode())
        # We are interested in the video stream, but will return all streams for now
        # video_streams = [s for s in data.get('streams', []) if s.get('codec_type') == 'video']
        # if not video_streams:
        #     return None # No video stream found
        # return video_streams[0]
        return data # Return all format and stream info
    except json.JSONDecodeError:
        # print("Error: Could not decode ffprobe JSON output.")
        return None

async def _is_ffmpeg_available():
    """Checks if ffmpeg is available in PATH."""
    process = await asyncio.create_subprocess_shell(
        "ffmpeg -version",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    return process.returncode == 0

async def compress_video_async(input_path: str, output_path: str, crf: int = 28) -> bool:
    """
    Compresses a video file using ffmpeg.

    Args:
        input_path: Path to the input video file.
        output_path: Path to save the compressed video file.
        crf: Constant Rate Factor (0-51, lower is better quality, 23-28 is common).

    Returns:
        True if compression was successful, False otherwise.
        Raises FileNotFoundError if ffmpeg is not installed/found.
    """
    if not await _is_ffmpeg_available():
        raise FileNotFoundError("ffmpeg command not found. Please install ffmpeg.")

    if not await aios.path.isfile(input_path):
        # print(f"Error: Input video file '{input_path}' not found.")
        return False

    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir: # If output_path includes a directory
        await aios.mkdir(output_dir, exist_ok=True)

    command = [
        "ffmpeg",
        "-i", input_path,
        "-c:v", "libx264",  # H.264 codec
        "-crf", str(crf),   # Constant Rate Factor
        "-preset", "medium", # Encoding speed vs. compression (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
        "-c:a", "aac",      # AAC audio codec
        "-b:a", "128k",     # Audio bitrate
        "-y",               # Overwrite output file if it exists
        output_path
    ]

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()

    if process.returncode == 0:
        return True
    else:
        # print(f"Error during ffmpeg compression: {stderr.decode()}")
        return False

from PIL import Image # Placed here to ensure it's imported after potential installation
import io

async def extract_image_info_async(image_path: str) -> dict | None:
    """
    Extracts basic image information (format, mode, size) using Pillow.
    Uses asyncio.to_thread for non-blocking file operations.

    Args:
        image_path: The path to the image file.

    Returns:
        A dictionary with image info (format, mode, width, height), or None if
        the file is not a valid image or an error occurs.
    """
    if not await aios.path.isfile(image_path):
        return None

    try:
        # Read file asynchronously, then pass bytes to Image.open
        async with aiofiles.open(image_path, 'rb') as f:
            image_bytes = await f.read()

        # Pillow's Image.open and other operations are synchronous
        # Run them in a separate thread to avoid blocking asyncio loop
        def process_image(img_bytes):
            with Image.open(io.BytesIO(img_bytes)) as img:
                return {
                    "format": img.format,
                    "mode": img.mode,
                    "width": img.width,
                    "height": img.height,
                    "info": {k: v for k, v in img.info.items() if isinstance(v, (str, int, float, bool, list, dict, tuple))} # Filter exif
                }

        return await asyncio.to_thread(process_image, image_bytes)
    except FileNotFoundError: # Should be caught by aios.path.isfile, but as a safeguard
        return None
    except Exception as e: # Catches Pillow specific errors like UnidentifiedImageError
        # print(f"Error processing image {image_path}: {e}")
        return None

if __name__ == '__main__':
    async def main():
        # Create dummy files and directories for testing
        test_dir = "test_scan_dir"
        os.makedirs(os.path.join(test_dir, "subdir"), exist_ok=True)
        dummy_files_content = {
            "video.mp4": "dummy video content for md5",
            "audio.mp3": "dummy audio content for md5",
            "text.txt": "dummy text content for md5",
            "image.jpg": "dummy image content for md5",
            "unknown.dat": "dummy data content for md5",
            os.path.join("subdir", "script.py"): "dummy script content for md5"
        }

        for fname, content in dummy_files_content.items():
            full_path = os.path.join(test_dir, fname)
            os.makedirs(os.path.dirname(full_path), exist_ok=True) # ensure subdir exists
            with open(full_path, "w") as f: f.write(content)

        print("Scanning for file info (scan_folder_files_info):")
        try:
            scanned_files = await scan_folder_files_info("test_scan_dir")
            for f_info in scanned_files:
                print(f"  Name: {f_info['name']}, Path: {f_info['path']}, Type: {f_info['type']}")
        except ValueError as e:
            print(f"Error: {e}")

        print("\nScanning folder contents (scan_folder_contents):")
        try:
            folder_contents = await scan_folder_contents("test_scan_dir")
            for item_info in folder_contents:
                print(f"  Name: {item_info['name']}, Path: {item_info['path']}, Type: {item_info['type']}")
        except ValueError as e:
            print(f"Error: {e}")

        print("\nGenerating MD5 checksums (generate_md5_async):")
        test_file_for_md5 = os.path.join(test_dir, "text.txt")
        md5_sum = await generate_md5_async(test_file_for_md5)
        if md5_sum:
            print(f"  MD5 for '{test_file_for_md5}': {md5_sum}")
        else:
            print(f"  Could not generate MD5 for '{test_file_for_md5}' (file not found).")

        non_existent_file = os.path.join(test_dir, "non_existent.txt")
        md5_sum_non_existent = await generate_md5_async(non_existent_file)
        if md5_sum_non_existent:
            print(f"  MD5 for '{non_existent_file}': {md5_sum_non_existent}")
        else:
            print(f"  Could not generate MD5 for '{non_existent_file}' (file not found).")

        print("\nExtracting video info (extract_video_info_async):")
        # We know ffprobe is likely not installed in this environment,
        # so we expect a FileNotFoundError or the function to handle it.
        # For a real test, a small valid video file would be needed.
        dummy_video_file = os.path.join(test_dir, "video.mp4") # This is a text file

        # Create a tiny dummy "video" file for ffprobe to attempt to parse
        # ffprobe will fail to parse it as video, but it tests the command execution path
        # if ffprobe itself is found.
        async with aiofiles.open(dummy_video_file, "wb") as f: # write some bytes
            await f.write(b"this is not a real video file")

        try:
            video_info = await extract_video_info_async(dummy_video_file)
            if video_info:
                print(f"  Video info for '{dummy_video_file}':")
                # print(json.dumps(video_info, indent=2)) # Pretty print
                # For brevity in this test, just print a summary
                if 'format' in video_info:
                    print(f"    Format: {video_info['format'].get('format_name', 'N/A')}")
                if 'streams' in video_info and len(video_info['streams']) > 0:
                    print(f"    Codec (first stream): {video_info['streams'][0].get('codec_name', 'N/A')}")
                else:
                    print("    No streams found or ffprobe could not parse.")
            elif await aios.path.isfile(dummy_video_file):
                 print(f"  Could not extract video info for '{dummy_video_file}' (likely not a valid video or ffprobe error).")
            # else case is handled by the function returning None if file not found initially
        except FileNotFoundError as e:
            print(f"  Error: {e}")
        except Exception as e:
            print(f"  An unexpected error occurred: {e}")

        print("\nCompressing video (compress_video_async):")
        # We know ffmpeg is likely not installed, expect FileNotFoundError.
        # For a real test, a small valid video file would be needed.
        dummy_input_video = os.path.join(test_dir, "video.mp4") # This is a text file, not a real video
        dummy_output_video = os.path.join(test_dir, "video_compressed.mp4")

        # Ensure the dummy input "video" file exists (it was created for ffprobe test)
        # async with aiofiles.open(dummy_input_video, "wb") as f:
        #     await f.write(b"this is not a real video file, for compression test")

        try:
            success = await compress_video_async(dummy_input_video, dummy_output_video)
            if success:
                print(f"  Video '{dummy_input_video}' compressed to '{dummy_output_video}'.")
                if await aios.path.exists(dummy_output_video):
                    print(f"  Compressed file '{dummy_output_video}' created.")
                    await aios.remove(dummy_output_video) # Clean up
            else:
                # This path will also be taken if the input file is not found by compress_video_async
                if await aios.path.isfile(dummy_input_video): # Check if it's due to ffmpeg error vs file not found
                    print(f"  Video compression failed for '{dummy_input_video}'. (Likely due to invalid file or ffmpeg error)")
                # else:
                #    print(f"  Input video file '{dummy_input_video}' not found for compression.")

        except FileNotFoundError as e:
            print(f"  Error: {e}")
        except Exception as e:
            print(f"  An unexpected error occurred during compression test: {e}")

        print("\nExtracting image info (extract_image_info_async):")
        dummy_image_file = os.path.join(test_dir, "image.png") # Changed from .jpg to .png for dummy creation
        actual_image_file_for_test = os.path.join(test_dir, "test_image.png")
        non_image_file = os.path.join(test_dir, "text.txt") # Use existing text file

        # Create a small, valid PNG image for testing using Pillow
        try:
            img = Image.new('RGB', (60, 30), color = 'red')
            img.save(actual_image_file_for_test, 'PNG')

            image_info = await extract_image_info_async(actual_image_file_for_test)
            if image_info:
                print(f"  Image info for '{actual_image_file_for_test}':")
                print(f"    Format: {image_info['format']}, Mode: {image_info['mode']}, Size: {image_info['width']}x{image_info['height']}")
            else:
                print(f"  Could not extract image info for '{actual_image_file_for_test}'.")

            # Test with a non-image file
            non_image_info = await extract_image_info_async(non_image_file)
            if non_image_info:
                print(f"  Image info for non-image '{non_image_file}': {non_image_info}")
            else:
                print(f"  Correctly failed to extract image info from non-image file '{non_image_file}'.")

            # Test with a non-existent file
            non_existent_image_info = await extract_image_info_async("non_existent.png")
            if non_existent_image_info:
                 print(f"  Image info for non-existent file: {non_existent_image_info}")
            else:
                print(f"  Correctly failed for non-existent image file.")

        except ImportError:
            print("  Pillow library is not installed. Skipping image info test.")
        except Exception as e:
            print(f"  An error occurred during image info test setup or execution: {e}")
        finally:
            if await aios.path.exists(actual_image_file_for_test):
                await aios.remove(actual_image_file_for_test)


        # Clean up dummy files and directories
        # for fname in dummy_files_content.keys():
        #    full_path = os.path.join(test_dir, fname)
        #    if os.path.exists(full_path):
        #        os.remove(full_path)
        # if os.path.exists(os.path.join(test_dir, "subdir")):
        #    os.rmdir(os.path.join(test_dir, "subdir"))
        # if os.path.exists(test_dir):
        #    os.rmdir(test_dir)

        # --- Final Cleanup ---
        print("\n--- Cleaning up test files and directories ---")
        # Remove files first
        for fname_key in dummy_files_content.keys():
            # Handle nested file paths like "subdir/script.py"
            path_parts = fname_key.split('/')
            full_path = os.path.join(test_dir, *path_parts)
            if await aios.path.exists(full_path) and await aios.path.isfile(full_path):
                try:
                    await aios.remove(full_path)
                    print(f"  Removed file: {full_path}")
                except Exception as e:
                    print(f"  Error removing file {full_path}: {e}")

        # Remove subdir if it exists and is empty
        subdir_path = os.path.join(test_dir, "subdir")
        if await aios.path.exists(subdir_path) and await aios.path.isdir(subdir_path):
            try:
                # Check if subdir is empty, aios.listdir might be needed if not empty
                if not await aios.listdir(subdir_path): # Only remove if empty
                    await aios.rmdir(subdir_path)
                    print(f"  Removed directory: {subdir_path}")
                else:
                    print(f"  Directory not empty, not removing: {subdir_path}")
            except Exception as e:
                print(f"  Error removing directory {subdir_path}: {e}")

        # Remove main test directory if it exists and is empty
        if await aios.path.exists(test_dir) and await aios.path.isdir(test_dir):
            try:
                if not await aios.listdir(test_dir): # Only remove if empty
                    await aios.rmdir(test_dir)
                    print(f"  Removed directory: {test_dir}")
                else:
                    # List remaining items if not empty, for debugging
                    remaining_items = await aios.listdir(test_dir)
                    print(f"  Directory '{test_dir}' not empty, not removing. Remaining: {remaining_items}")
            except Exception as e:
                print(f"  Error removing directory {test_dir}: {e}")
        print("--- Test run complete ---")


    asyncio.run(main())
