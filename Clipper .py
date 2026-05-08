"""
YouTube -> Auto Clipper (YouTube Videos + Shorts/Reels)
--------------------------------------------------------
Produces TWO types of output from one long video:
  - output/youtube/  : 3-10 minute videos for YouTube
  - output/shorts/   : up to 60 second clips for Shorts & Reels

Usage:
    python clipper.py "https://youtube.com/watch?v=XXXXX"

Requirements:
    pip install yt-dlp openai-whisper anthropic
    ffmpeg must be installed (winget install ffmpeg)

Set your API key once before running:
    Windows:   set ANTHROPIC_API_KEY=sk-ant-...
"""

import subprocess
import sys
import os
import json
import re
import anthropic

# ── CONFIG ─────────────────────────────────────────────────────────────────────
WHISPER_MODEL = "base"      # tiny | base | small | medium  (bigger = slower + more accurate)
OUTPUT_DIR    = "output"    # root output folder

# YouTube long-form clips
YT_MIN_SECONDS  = 180       # 3 minutes minimum
YT_MAX_SECONDS  = 600       # 10 minutes maximum
YT_CLIP_COUNT   = 3         # how many long YouTube clips to make

# Shorts / Reels clips
SHORT_MIN_SECONDS = 20      # 20 seconds minimum
SHORT_MAX_SECONDS = 60      # 60 seconds maximum
SHORT_CLIP_COUNT  = 6       # how many short clips to make

# Use python -m so PATH doesn't matter on Windows
PYTHON      = sys.executable   # exact python being used right now
YT_DLP      = f'"{PYTHON}" -m yt_dlp'
WHISPER_CMD = f'"{PYTHON}" -m whisper'
# ───────────────────────────────────────────────────────────────────────────────


def run(cmd, desc=""):
    print(f"\n>>> {desc}\n")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"ERROR: command failed — see above for details")
        sys.exit(1)


def srt_to_text(srt_path):
    with open(srt_path, "r", encoding="utf-8") as f:
        return f.read()


def ask_claude_for_clips(transcript, video_title):
    client = anthropic.Anthropic()

    prompt = f"""You are a professional video editor who specialises in repurposing long YouTube videos into multiple formats.

Video title: "{video_title}"

Below is an SRT transcript. I need TWO lists of clips:

--- LIST 1: YOUTUBE VIDEOS ({YT_CLIP_COUNT} clips) ---
These are 3-10 minute self-contained segments for YouTube.
Pick topics/stories/sections that have a clear beginning, middle and end.
They should feel like a complete mini-video someone would watch and share.
Length: {YT_MIN_SECONDS} to {YT_MAX_SECONDS} seconds each.

--- LIST 2: SHORTS AND REELS ({SHORT_CLIP_COUNT} clips) ---
These are punchy clips under 60 seconds for YouTube Shorts and Instagram Reels.
Pick the most surprising, funny, emotional, or mind-blowing single moments.
The first 3 seconds MUST be a hook that stops someone mid-scroll.
Length: {SHORT_MIN_SECONDS} to {SHORT_MAX_SECONDS} seconds each.

Use the EXACT timestamps from the SRT file (format HH:MM:SS,mmm).

Respond ONLY with valid JSON — no explanation, no markdown fences. Use this exact structure:
{{
  "youtube_clips": [
    {{
      "start": "00:02:10,000",
      "end": "00:07:45,000",
      "title": "Full YouTube video title here",
      "description": "2-3 sentence YouTube description with keywords",
      "reason": "Why this works as a standalone video"
    }}
  ],
  "short_clips": [
    {{
      "start": "00:04:22,000",
      "end": "00:05:10,000",
      "hook": "Nobody tells you this...",
      "youtube_title": "Short punchy title #Shorts",
      "instagram_caption": "Caption here\\n\\n#reels #shorts #viral",
      "reason": "Why this moment grabs attention"
    }}
  ]
}}

SRT TRANSCRIPT:
{transcript[:14000]}
"""

    print(">>> Sending transcript to Claude...")
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        result = json.loads(raw)
        yt_count    = len(result.get("youtube_clips", []))
        short_count = len(result.get("short_clips", []))
        print(f"    Claude found {yt_count} YouTube clips and {short_count} short clips.")
        return result
    except json.JSONDecodeError:
        print("ERROR: Claude returned invalid JSON. Raw output:")
        print(raw[:500])
        sys.exit(1)


def srt_time_to_seconds(t):
    t = t.replace(",", ".")
    h, m, s = t.split(":")
    return float(h) * 3600 + float(m) * 60 + float(s)


def seconds_to_ffmpeg(s):
    h   = int(s // 3600)
    m   = int((s % 3600) // 60)
    sec = s % 60
    return f"{h:02d}:{m:02d}:{sec:06.3f}"


def safe_filename(text, max_len=40):
    return re.sub(r'[^\w\s-]', '', text)[:max_len].strip().replace(" ", "_")


def cut_youtube_clip(video_path, clip, index, out_dir):
    """Cut a long-form YouTube clip — keeps original 16:9 aspect ratio."""
    start_s  = srt_time_to_seconds(clip["start"])
    end_s    = srt_time_to_seconds(clip["end"])
    duration = end_s - start_s

    if not (YT_MIN_SECONDS <= duration <= YT_MAX_SECONDS + 60):
        print(f"    Skipping YT clip {index} — duration {duration:.0f}s out of range")
        return

    fname    = f"yt_{index:02d}_{safe_filename(clip['title'])}.mp4"
    out_path = os.path.join(out_dir, fname)

    cmd = (
        f'ffmpeg -y '
        f'-ss {seconds_to_ffmpeg(start_s)} '
        f'-i "{video_path}" '
        f'-t {seconds_to_ffmpeg(duration)} '
        f'-c:v libx264 -preset fast -crf 20 '
        f'-c:a aac -b:a 192k '
        f'"{out_path}"'
    )
    run(cmd, f"Cutting YouTube clip {index}: {clip['title'][:60]}")

    meta_path = out_path.replace(".mp4", "_meta.txt")
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(f"YOUTUBE TITLE:\n{clip['title']}\n\n")
        f.write(f"DESCRIPTION:\n{clip['description']}\n\n")
        f.write(f"TIMESTAMPS: {clip['start']} to {clip['end']}\n")
        f.write(f"LENGTH: {duration/60:.1f} minutes\n\n")
        f.write(f"WHY THIS WORKS:\n{clip.get('reason','')}\n")

    print(f"    Saved: {out_path}  ({duration/60:.1f} min)")


def cut_short_clip(video_path, clip, index, out_dir):
    """Cut a short clip and crop to 9:16 vertical for Shorts/Reels."""
    start_s  = srt_time_to_seconds(clip["start"])
    end_s    = srt_time_to_seconds(clip["end"])
    duration = end_s - start_s

    if not (SHORT_MIN_SECONDS <= duration <= SHORT_MAX_SECONDS + 10):
        print(f"    Skipping short clip {index} — duration {duration:.0f}s out of range")
        return

    fname    = f"short_{index:02d}_{safe_filename(clip['hook'])}.mp4"
    out_path = os.path.join(out_dir, fname)

    # Center-crop 1920x1080 (16:9) to 1080x1920 (9:16)
    crop_filter = "crop=608:1080:656:0,scale=1080:1920"

    cmd = (
        f'ffmpeg -y '
        f'-ss {seconds_to_ffmpeg(start_s)} '
        f'-i "{video_path}" '
        f'-t {seconds_to_ffmpeg(duration)} '
        f'-vf "{crop_filter}" '
        f'-c:v libx264 -preset fast -crf 23 '
        f'-c:a aac -b:a 128k '
        f'"{out_path}"'
    )
    run(cmd, f"Cutting short clip {index}: {clip['hook'][:50]}")

    meta_path = out_path.replace(".mp4", "_meta.txt")
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(f"HOOK (first 3 seconds text overlay):\n{clip['hook']}\n\n")
        f.write(f"YOUTUBE SHORTS TITLE:\n{clip['youtube_title']}\n\n")
        f.write(f"INSTAGRAM REEL CAPTION:\n{clip['instagram_caption']}\n\n")
        f.write(f"TIMESTAMPS: {clip['start']} to {clip['end']}\n")
        f.write(f"LENGTH: {duration:.0f} seconds\n\n")
        f.write(f"WHY THIS WORKS:\n{clip.get('reason','')}\n")

    print(f"    Saved: {out_path}  ({duration:.0f}s)")


def check_requirements():
    print("\n=== Checking requirements ===")
    ok = True

    # Check ffmpeg (must be on PATH, installed via winget)
    result = subprocess.run("ffmpeg -version", shell=True, capture_output=True)
    if result.returncode == 0:
        print("    [OK] ffmpeg")
    else:
        print("    [MISSING] ffmpeg — run: winget install ffmpeg  then restart terminal")
        ok = False

    # Check yt-dlp via python -m
    result = subprocess.run(f"{YT_DLP} --version", shell=True, capture_output=True)
    if result.returncode == 0:
        print("    [OK] yt-dlp")
    else:
        print("    [MISSING] yt-dlp — run: pip install yt-dlp")
        ok = False

    # Check whisper via python -m (whisper has no --help, so we check --version which exits with error but still means it's installed)
    result = subprocess.run(f"{WHISPER_CMD} --version", shell=True, capture_output=True)
    if "audio" in result.stderr.decode() or "audio" in result.stdout.decode() or "whisper" in result.stderr.decode().lower():
        print("    [OK] whisper")
    else:
        print("    [MISSING] whisper — run: pip install openai-whisper")
        ok = False

    # Check API key
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("    [OK] ANTHROPIC_API_KEY")
    else:
        print("    [MISSING] ANTHROPIC_API_KEY — run: set ANTHROPIC_API_KEY=sk-ant-...")
        ok = False

    if not ok:
        print("\nFix the missing items above then run again.")
        sys.exit(1)

    print("    All good — starting!\n")


def main():
    if len(sys.argv) < 2:
        print("Usage: python clipper.py \"https://youtube.com/watch?v=...\"")
        sys.exit(1)

    url = sys.argv[1]
    check_requirements()

    yt_dir    = os.path.join(OUTPUT_DIR, "youtube")
    short_dir = os.path.join(OUTPUT_DIR, "shorts")
    os.makedirs(yt_dir,    exist_ok=True)
    os.makedirs(short_dir, exist_ok=True)

    # ── STEP 1: Download ───────────────────────────────────────────────────────
    print("=== STEP 1: Downloading video ===")
    video_path = os.path.join(OUTPUT_DIR, "video.mp4")

    if os.path.exists(video_path):
        print("    video.mp4 already exists — skipping download")
    else:
        run(
            f'{YT_DLP} -f "bestvideo[height<=1080]+bestaudio/best[height<=1080]" '
            f'--merge-output-format mp4 '
            f'--write-info-json '
            f'-o "{OUTPUT_DIR}/video.%(ext)s" "{url}"',
            "Downloading with yt-dlp"
        )

    # Try to get video title
    video_title = "YouTube video"
    info_path = os.path.join(OUTPUT_DIR, "video.info.json")
    if os.path.exists(info_path):
        try:
            with open(info_path) as f:
                info = json.load(f)
                video_title = info.get("title", video_title)
        except Exception:
            pass
    print(f"    Title: {video_title}")

    # ── STEP 2: Transcribe ─────────────────────────────────────────────────────
    print("\n=== STEP 2: Transcribing with Whisper ===")
    srt_path = os.path.join(OUTPUT_DIR, "transcript.srt")

    if os.path.exists(srt_path):
        print("    transcript.srt already exists — skipping transcription")
    else:
        run(
            f'{WHISPER_CMD} "{video_path}" '
            f'--model {WHISPER_MODEL} '
            f'--output_format srt '
            f'--output_dir "{OUTPUT_DIR}" '
            f'--language en',
            f"Transcribing with Whisper (model: {WHISPER_MODEL})"
        )
        # Whisper names the file after the video — rename to transcript.srt
        for fname in os.listdir(OUTPUT_DIR):
            if fname.endswith(".srt") and fname != "transcript.srt":
                os.rename(os.path.join(OUTPUT_DIR, fname), srt_path)
                break

    transcript = srt_to_text(srt_path)
    print(f"    Transcript loaded — {len(transcript)} characters")

    # ── STEP 3: Claude picks clips ─────────────────────────────────────────────
    print("\n=== STEP 3: Claude finding clips ===")
    clips_data = ask_claude_for_clips(transcript, video_title)

    with open(os.path.join(OUTPUT_DIR, "clips.json"), "w") as f:
        json.dump(clips_data, f, indent=2)
    print("    Clip list saved to output/clips.json")

    # ── STEP 4: Cut YouTube clips ──────────────────────────────────────────────
    print("\n=== STEP 4: Cutting YouTube long-form clips ===")
    for i, clip in enumerate(clips_data.get("youtube_clips", []), 1):
        cut_youtube_clip(video_path, clip, i, yt_dir)

    # ── STEP 5: Cut Shorts/Reels ───────────────────────────────────────────────
    print("\n=== STEP 5: Cutting Shorts and Reels ===")
    for i, clip in enumerate(clips_data.get("short_clips", []), 1):
        cut_short_clip(video_path, clip, i, short_dir)

    # ── Summary ────────────────────────────────────────────────────────────────
    print("\n" + "="*55)
    print("DONE!")
    print(f"  output/youtube/  — long-form YouTube clips (3-10 min)")
    print(f"  output/shorts/   — Shorts + Reels clips (max 60s, vertical)")
    print("  Each clip has a _meta.txt with the title and caption.")
    print("="*55)


if __name__ == "__main__":
    main()
