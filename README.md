# 🎬 Colabvid 2.0

<p align="center">
  <a href="https://colab.research.google.com/github/Faroffcode/Colabvid2.0/blob/upload-speed-test/Colabvid_2.0.ipynb">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" />
  </a>
</p>

A modular Google Colab Telegram bot for downloading videos, creating vertical clips, and uploading the results to a Telegram channel with unified progress reporting.

> 🧪 **Testing branch:** This README and the Colab instructions use the `upload-speed-test` branch, which contains the current upload-speed testing changes, Pyrogram upload integration, and video thumbnail support.

## 🚀 Open the updated code in Google Colab

Use this link to open the **latest updated notebook from the `upload-speed-test` branch**:

👉 **[🚀 Open Updated Colab Notebook](https://colab.research.google.com/github/Faroffcode/Colabvid2.0/blob/upload-speed-test/Colabvid_2.0.ipynb)**

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Faroffcode/Colabvid2.0/blob/upload-speed-test/Colabvid_2.0.ipynb)

Open the notebook directly in Google Colab, run the installation cell, enter your configuration, verify the setup, and start the bot.

## ✨ Features

- 📥 Download videos from supported direct URLs and Pixeldrain links
- 🎬 Create 9:16 vertical clips at 1080×1920 resolution
- 🖼️ Preserve the complete video frame using scale and padding
- 📤 Upload rendered clips to a Telegram channel
- 🖼️ Generate and attach video thumbnails during upload
- 📊 Show download, encoding, and upload progress in one message
- 🔁 Retry failed uploads
- ⚡ Test optimized upload handling with Pyrogram
- ☁️ Designed for Google Colab
- 🧩 Modular project structure

## 🛠️ Google Colab setup

### Using the updated Colab notebook

1. Open the **[Updated Colab Notebook](https://colab.research.google.com/github/Faroffcode/Colabvid2.0/blob/upload-speed-test/Colabvid_2.0.ipynb)**.
2. Confirm that the notebook is opened from the `upload-speed-test` branch.
3. Run the installation cell.
4. Run the setup cell.
5. Enter your Telegram configuration when prompted.
6. Run the verification step below.
7. Run the bot startup cell.

### Manual setup

Clone the testing branch directly:

```python
!git clone --branch upload-speed-test https://github.com/Faroffcode/Colabvid2.0.git
%cd Colabvid2.0
!pip install -r requirements.txt
!python colab_setup.py
```

If the repository has already been cloned, switch to the testing branch with:

```bash
git fetch origin upload-speed-test
git checkout upload-speed-test
git pull origin upload-speed-test
```

## ✅ Verification step

Run this verification cell **before starting the bot**. It checks that the correct branch is active, the main Python files compile, and the required environment variables are available without printing secret values.

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

if branch != "upload-speed-test":
    raise RuntimeError(
        f"Wrong branch: {branch!r}. Expected 'upload-speed-test'."
    )

print("\n🐍 Checking Python files...")
result = subprocess.run(
    [sys.executable, "-m", "compileall", "-q", "app.py", "config.py", "bot", "core", "services"],
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

> **Telegram upload check:** If you receive `Peer id invalid`, confirm that the bot is a member of the target channel and has permission to post videos. Also run the Pyrogram channel/dialog verification test provided in the troubleshooting instructions before changing the channel ID.

## 🔐 Required configuration

The setup script asks for these values in one place:

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

Send a supported video URL to the Telegram bot to begin processing.

## ⚙️ Current defaults

- Clip duration: 60 seconds
- Clip count: 5
- Output size: 1080×1920
- Upload retries: 2
- Upload testing branch: `upload-speed-test`

## 👨‍💻 Developer

**Imtiaz Haque (Faroff)**

## 📄 License

Add a license before distributing the project publicly.
