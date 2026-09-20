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

## Google Colab setup

The repository includes `colab_setup.py`, which asks for the required environment values interactively and loads them into the current Colab session.

Run this in a Colab cell:

```python
!git clone https://github.com/Faroffcode/Colabvid2.0.git
%cd Colabvid2.0
!pip install -r requirements.txt
!python colab_setup.py
```

Enter these values when prompted:

- `COLABVID_API_ID`
- `COLABVID_API_HASH`
- `COLABVID_BOT_TOKEN`
- `COLABVID_CHANNEL_ID`

The API hash and bot token are entered using hidden input. The values are loaded only into the active Colab session and are not written into the repository.

Start the bot after setup:

```python
!python app.py
```

## Project goals

- Small, readable Python modules
- Clear separation between Telegram, downloading, rendering, and uploading
- Retry and resume support
- Google Colab compatibility

## Status

🚧 Initial project setup
