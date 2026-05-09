# AI Video Clipper — Free YouTube to Shorts and Reels

Automatically turn any long YouTube video into ready-to-upload clips using local AI. No subscriptions. No uploads to third-party servers. 100% free.

Supports Arabic and English (and 90+ other languages via Whisper).

---

## What it does

Give it a YouTube URL. It will:

1. Download the video with yt-dlp
2. Transcribe the audio locally with OpenAI Whisper
3. Analyse the transcript with AI and pick the best moments
4. Cut and export two sets of clips automatically with ffmpeg

Output folders:
- output/youtube/ — 3 to 10 minute standalone YouTube videos
- output/shorts/ — Up to 60 second vertical 9:16 clips for YouTube Shorts and Instagram Reels

Each clip comes with a text file containing a ready-to-paste title, description, and Instagram caption.

---

## Why this beats paid clipping tools

Paid tools like OpusClip and Vidyo cost $30 to $50 per month, only work in English, upload your videos to their servers, and only produce short clips. This tool is free forever, supports Arabic natively, runs entirely on your own computer, and produces both long YouTube cuts and short vertical clips in one run.

---

## Requirements

- Windows, Mac, or Linux
- Python 3.8 or higher
- ffmpeg
- Either an Anthropic API key OR Ollama installed locally (both options explained below)

---

## Installation

### Step 1 — Install ffmpeg

Windows:
```
winget install ffmpeg
```

Mac:
```
brew install ffmpeg
```

Linux:
```
sudo apt install ffmpeg
```

Restart your terminal after installing.

### Step 2 — Install Python packages

```
pip install yt-dlp openai-whisper anthropic
```

### Step 3 — Choose your AI backend

You have two options. Pick one.

---

#### Option A — Anthropic API (recommended, easy setup)

Free credits are given when you sign up. Enough to process dozens of videos.

1. Go to console.anthropic.com and create an account
2. Click API Keys on the left sidebar
3. Click Create Key, give it any name, copy the key

Set the key in your terminal:

Windows:
```
set ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

Mac/Linux:
```
export ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
```

To set it permanently on Windows so you never have to do this again:
```
setx ANTHROPIC_API_KEY "sk-ant-YOUR_KEY_HERE"
```

In clipper.py make sure this line is set:
```
AI_BACKEND = "anthropic"
```

---

#### Option B — Ollama (100% free forever, no account needed)

Ollama runs AI models directly on your computer. No API key, no account, no internet needed for the AI step.

1. Download and install Ollama from ollama.com
2. Open a terminal and pull a model:

```
ollama pull llama3
```

Wait for it to download (about 4GB). Then start the Ollama server:

```
ollama serve
```

Leave that terminal open. In clipper.py set:
```
AI_BACKEND = "ollama"
OLLAMA_MODEL = "llama3"
```

Note: Ollama works well for English. For Arabic content, Claude (Option A) gives better results. If you want to use Ollama with Arabic, try the aya model which has stronger Arabic support:
```
ollama pull aya
```
Then set OLLAMA_MODEL = "aya" in the script.

---

## Usage

```
python clipper.py "https://youtube.com/watch?v=XXXXX"
```

That is the entire command. The script handles everything automatically and prints its progress as it goes.

---

## Output structure

```
output/
  video.mp4                       downloaded source video
  transcript.srt                  full transcript, reused on reruns
  clips.json                      all clip data from the AI
  youtube/
    yt_01_Title.mp4               3 to 10 minute YouTube video
    yt_01_Title_meta.txt          title and description
  shorts/
    short_01_Hook.mp4             max 60 seconds, vertical 9:16
    short_01_Hook_meta.txt        hook, YouTube title, Instagram caption
```

---

## Configuration

Open clipper.py and edit the CONFIG section at the top:

```
AI_BACKEND    = "anthropic"   change to "ollama" for fully local AI
OLLAMA_MODEL  = "llama3"      only used when AI_BACKEND is ollama
WHISPER_MODEL = "small"       tiny / base / small / medium
YT_CLIP_COUNT    = 3          how many long YouTube clips to generate
SHORT_CLIP_COUNT = 6          how many Shorts and Reels to generate
```

For Arabic videos the script is already set to transcribe in Arabic and sends the prompt in Arabic. For other languages find the line --language ar and change ar to your language code such as en for English or fr for French.

---

## Whisper model guide

- tiny — very fast, basic quality, good for quick tests
- base — fast, okay quality
- small — medium speed, good quality, recommended for most videos
- medium — slow, great quality, best for Arabic and non-English content
- to adjust the language, edit "f'--language en" in code and change en to ar or the language wanted

---

## Tips

The transcript is saved and reused. If you run the same video twice Whisper will not re-transcribe it, only the AI step reruns. This saves a lot of time.

If the video is already downloaded the download step is skipped too.

API credits are only used in Step 3. Steps 1, 2, 4, and 5 are completely free regardless of which backend you use.

The crop assumes 1920x1080 source video. If your source is a different resolution adjust the crop_filter line in the cut_short_clip function.

---

## How it works

```
YouTube URL
    ↓
yt-dlp downloads video.mp4
    ↓
Whisper transcribes audio to transcript.srt  (runs locally, free)
    ↓
Claude or Ollama reads transcript, picks best clips, writes titles and captions
    ↓
ffmpeg cuts clips and crops shorts to vertical 9:16
    ↓
output/youtube/  and  output/shorts/
```

---

## Contributing

Pull requests welcome. Ideas for future features:
- Auto-burn captions onto short clips
- Automatic thumbnail generation
- Direct upload to YouTube and Instagram via their APIs
- A simple GUI so no terminal is needed

---

## License

MIT — free to use, modify, and share.

---

Built by someone who was tired of paying $40 a month for clipping tools.
