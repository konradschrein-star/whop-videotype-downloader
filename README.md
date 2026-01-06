# Whop & M3U8 Downloader

A clean, modern, and user-friendly tool intended to organize and download course videos (or any m3u8 streams) efficiently. It is built with Python and Tkinter, providing a robust GUI for managing your downloads.

## Features
*   **Queue System**: Load a text file with links, and the app automatically parses and categorizes them into folders (e.g., "AI", "Marketing", "Technical") based on keywords.
*   **Drag & Drop**: Easily reorganize your video queue by dragging videos into different folders within the app.
*   **Fast Downloads**: Uses efficient stream copying (`-c copy`) so downloads are lightning fast and quality is 1:1 with the source.
*   **Audio Only Mode**: Option to download just the audio (`.mp3`) for listening on the go.
*   **Smart Clipboard**: "Watch Clipboard" mode detects when you copy an `.m3u8` link and instantly asks to add it to your queue.
*   **Dark Mode**: Toggle between Light and Dark themes.

## Prerequisites
**FFmpeg is REQUIRED** for this tool to work.
1.  Download `ffmpeg.exe` (e.g., from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)).
2.  Place `ffmpeg.exe` in the **same folder** as the Downloader executable.
    *   *Alternatively, install FFmpeg deeply into your system PATH.*

## How to Use
1.  **Get Links**: Use your browser's Developer Tools (Network Tab) to find the `.m3u8` stream URL of the video you want to play.
2.  **Create a List**: Save these links in a text file (Title on one line, URL on the next).
3.  **Load & Start**: Open the app, load your text file, and hit "START DOWNLOAD".

## Build from Source
If you want to modify the code or build the .exe yourself:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "WhopDownloader" Whop_and_m3u8_downloader.py
```
