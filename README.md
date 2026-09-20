# 🎬 Colabvid 2.0

<p align="center">
  <a href="https://colab.research.google.com/github/Faroffcode/Colabvid2.0/blob/main/Colabvid_2.0.ipynb">
    <img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab" />
  </a>
</p>

A modular Google Colab Telegram bot for downloading videos, creating vertical clips, and uploading the results to a Telegram channel with unified progress reporting.

## 🚀 Open in Google Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Faroffcode/Colabvid2.0/blob/main/Colabvid_2.0.ipynb)

Open the notebook directly in Google Colab, run the installation cell, enter your configuration, and start the bot.

## ✨ Features

- 📥 Download videos from supported direct URLs and Pixeldrain links
- 🎬 Create 9:16 vertical clips at 1080×1920 resolution
- 🖼️ Preserve the complete video frame using scale and padding
- 📤 Upload rendered clips to a Telegram channel
- 📊 Show download, encoding, and upload progress in one message
- 🔁 Retry failed uploads
- ☁️ Designed for Google Colab
- 🧩 Modular project structure

## 🛠️ Google Colab setup

### Using the Colab notebook

1. Click the **Open in Colab** button above.
2. Run the installation cell.
3. Run the setup cell.
4. Enter your Telegram configuration when prompted.
5. Run the bot startup cell.

### Manual setup

```python
!git clone https://github.com/Faroffcode/Colabvid2.0.git
%cd Colabvid2.0
!pip install -r requirements.txt
!python colab_setup.py
!python app.py
```

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

## 👨‍💻 Developer

**Imtiaz Haque (Faroff)**

## 📄 License

Add a license before distributing the project publicly.
