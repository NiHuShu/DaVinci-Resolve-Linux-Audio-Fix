# DaVinci Resolve Audio Fix (Linux)

A small Fusion script that works around DaVinci Resolve's missing audio codecs on
Linux. When you drop a clip onto the timeline, the video plays but the audio track
is usually **completely silent** because the free/Studio Linux build ships without certain
audio codecs (AAC, etc.).

The script is based on some random script that I found online years ago. It was updated to work with Resolve 21 + new functions were added (the playhead no longer has to be at the beginning of the script, the audio matches the clip length, and it automatically replaces the old audio clip).

This script:

1. Reads the video clip under the playhead.
2. Extracts its audio with `ffmpeg`, trimmed to **only the visible portion** of the
   clip on the timeline.
3. Removes the silent audio item that Resolve imported alongside the video.
4. Imports the converted `.wav` and places it at the **start of the clip**, in sync
   with the picture.

Converted files are cached in a temp folder, so re-running on the same clip/trim is instant.

## Why this exists

Resolve on Linux can't decode some audio codecs, so timelines end up silent. Rather
than re-encoding every source file by hand, this script does it on demand, per clip, straight from inside Resolve.

## Requirements

- DaVinci Resolve (free or Studio) on Linux
- `ffmpeg` and `ffprobe` installed and on your system
- The script run from **inside Resolve** (it uses the injected `bmd` object)

Check ffmpeg is installed:

```bash
ffmpeg -version
ffprobe -version
```

On Debian/Ubuntu: `sudo apt install ffmpeg`

## Installation

1. Copy `convertAudio.py` into your Resolve Comp scripts folder:

   ```
   ~/.local/share/DaVinciResolve/Fusion/Scripts/Comp/convertAudio.py
   ```

2. (Optional) Edit the paths at the top of the script if your setup differs:

   ```python
   outputDir = "/home/" + os.getlogin() + "/temp/"   # where WAVs are cached
   ffmpeg    = "/usr/bin/ffmpeg"
   ffprobe   = "/usr/bin/ffprobe"
   ```

   **Make sure `outputDir` exists** — create it if needed:

   ```bash
   mkdir -p ~/temp
   ```

## Usage

1. Add a clip to **video track 1** of your timeline.
2. Put the playhead anywhere on that clip.
3. Run the script: **Workspace → Scripts → Comp → convertAudio** (The script can be assigned to a keybaord shortcut)

The silent audio is removed and the real audio appears on audio track 1, at the start of the clip and in sync.

## Notes & limitations

- The script reads the clip from **video track 1**. If your clip is on another track,
  adjust `GetItemsInTrack("video", 1)`.
- The silent-audio removal deletes **any** audio item overlapping the video clip's
  span on the timeline. If you have unrelated audio (music, voiceover) under the clip,
  it may be removed too. Run this before layering other audio under the clip.
- `timeline.DeleteClips()` requires **Resolve 18 or newer**.
- `-ss` seeking is fast and accurate on modern ffmpeg builds. If audio ever drifts a
  few frames, move `-ss` to after `-i` in `buildFFmpegCommand()` (slower but
  sample-accurate).

## How it works

| Step | API / tool |
|------|-----------|
| Get clip under playhead | `timeline.GetCurrentVideoItem()` |
| Find source file path | `mediaPoolItem.GetClipProperty("File Path")` |
| Determine visible portion | `GetLeftOffset()`, `GetDuration()` |
| Extract + trim audio | `ffmpeg -ss … -i … -t … -af apad` |
| Remove silent audio | `timeline.DeleteClips()` (overlap match) |
| Place converted audio | `mediaPool.AppendToTimeline()` at `GetStart()` |

## Contributing

Issues and PRs welcome. This was built for a specific Linux workflow, so
improvements for other track layouts, codecs, or Resolve versions are appreciated.

## License

MIT — see [LICENSE](LICENSE).
