# 🎬 Colabvid 2.0

<p align="center">
  <a href="https://colab.research.google.com/github/Faroffcode/Colabvid2.0/blob/main/Colabvid_2.0.ipynb">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" />
  </a>
</p>

A modular Google Colab Telegram bot for downloading videos, creating vertical clips, and uploading the results to a Telegram channel with unified progress reporting.

The project is designed for Google Colab testing and supports automatic source-video metadata detection before processing.

## 🚀 Open in Google Colab

Open the latest notebook from the `main` branch:

👉 **[🚀 Open Colabvid 2.0 in Google Colab](https://colab.research.google.com/github/Faroffcode/Colabvid2.0/blob/main/Colabvid_2.0.ipynb)**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Faroffcode/Colabvid2.0/blob/main/Colabvid_2.0.ipynb)

The notebook installs the project, prepares the Colab environment, and starts the Telegram bot. Follow the configuration prompts before launching the bot.

## ✨ Features

- 📥 Download videos from supported direct URLs and supported video services
- 🔎 Automatically detect source-video title and duration
- 🛠️ Use yt-dlp metadata extraction with FFprobe fallback for direct media URLs
- 🎬 Create 9:16 vertical clips at 1080×1920 resolution
- 🖼️ Preserve the complete video frame using scaling and padding
- 📤 Upload rendered clips to a Telegram channel
- 🖼️ Generate and attach video thumbnails during upload
- 📊 Show download, encoding, and upload progress through Telegram notifications
- 🔁 Retry failed uploads
- ⚡ Use Pyrogram for video uploads
- 📢 Configure the destination channel using `/setchannel`
- ☁️ Designed for Google Colab
- 🧩 Modular project structure

## 🔎 Automatic video metadata detection

When you send a video URL to the bot, Colabvid attempts to detect the source metadata before asking for the custom filename.

The bot can display:

- 🎬 Source title
- ⏱️ Source duration

The detection process uses:

1. **yt-dlp** for supported webpage and media URLs.
2. **FFprobe** as a fallback for direct media URLs when yt-dlp cannot retrieve the duration.

Metadata detection does not download the complete video. Some protected, expired, or unsupported URLs may still return `Unknown` metadata.

## 🛠️ Google Colab setup

### Using the Colab notebook

1. Open the [Colab notebook](https://colab.research.google.com/github/Faroffcode/Colabvid2.0/blob/main/Colabvid_2.0.ipynb).
2. Run the installation cell.
3. Run the setup cell.
4. Enter your Telegram configuration when prompted.
5. Run the verification step.
6. Start the bot.

### Manual setup

Clone the `main` branch:

```python
!git clone --branch main https://github.com/Faroffcode/Colabvid2.0.git
%cd Colabvid2.0
!pip install -r requirements.txt
!python colab_setup.py
```

If the repository has already been cloned:

```bash
git fetch origin main
git checkout main
git pull origin main
```

## ✅ Verification step

Run this verification cell before starting the bot. It checks the active branch, compiles the main Python files, and verifies that required environment variables are present without printing secret values.

```python
import os
import subprocess
import sys

print("🔎 Checking active branch...")
branch = subprocess.check_output(
    ["git", "branch", "--show-current"],
    text=True,
).strip()
print(f"Branch: {branch}")

if branch != "main":
    raise RuntimeError(
        f"Wrong branch: {branch!r}. Expected 'main'."
    )

print("\n🐍 Checking Python files...")
result = subprocess.run(
    [
        sys.executable,
        "-m",
        "compileall",
        "-q",
        "app.py",
        "config.py",
        "bot",
        "core",
        "services",
    ],
    check=False,
)

if result.returncode != 0:
    raise RuntimeError("Python compilation check failed.")

print("✅ Python compilation passed.")

print("\n🔐 Checking required configuration...")
required = [
    "COLABVID_API_ID",
    "COLABVID_API_HASH",
    "COLABVID_BOT_TOKEN",
    "COLABVID_CHANNEL_ID",
]

missing = [name for name in required if not os.getenv(name, "").strip()]

if missing:
    raise RuntimeError(
        "Missing configuration variables: " + ", ".join(missing)
    )

print("✅ Required configuration variables are present.")
print("\n🎉 Verification completed successfully. You can now start the bot.")
```

> **Telegram upload check:** If you receive `Peer id invalid`, confirm that the bot is a member of the target channel and has permission to post videos. You can use `/setchannel` to configure the destination by forwarding a message from the target channel.

## 🔐 Required configuration

The setup script asks for these values:

```text
COLABVID_API_ID
COLABVID_API_HASH
COLABVID_BOT_TOKEN
COLABVID_CHANNEL_ID
```

The API hash and bot token use hidden input. Keep all credentials private and never commit them to GitHub.

## 📁 Project structure

```text
Colabvid2.0/
├── app.py
├── config.py
├── colab_setup.py
├── Colabvid_2.0.ipynb
├── requirements.txt
├── bot/
├── core/
└── services/
```

## ▶️ Start the bot

```bash
python app.py
```

Then send a supported video URL to the Telegram bot. The bot will attempt to detect the source title and duration before asking for clip settings.

## ⚙️ Current defaults

- Clip duration: 60 seconds
- Clip count: 5
- Output size: 1080×1920
- Upload retries: 2
- Active branch: `main`
- Metadata detection: yt-dlp with FFprobe fallback

## 👨‍💻 Developer

**Imtiaz Haque (Faroff)**

## 📄 License

Add a license before distributing the project publicly.
