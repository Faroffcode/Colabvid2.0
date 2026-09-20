# Colabvid 2.0

A simple Google Colab Telegram bot for turning videos into vertical clips and uploading them to a Telegram channel.

## Planned workflow

1. Send a video URL to the Telegram bot.
2. Inspect and validate the URL.
3. Choose a filename, clip duration, and clip count.
4. Download the source video.
5. Create 9:16 clips with FFmpeg.
6. Upload clips to the configured Telegram channel.
7. Show download, encoding, and upload progress in one message.

## Project goals

- Small, readable Python modules
- Clear separation between Telegram, downloading, rendering, and uploading
- Retry and resume support
- Google Colab compatibility

## Status

🚧 Initial project setup
