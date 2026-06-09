#!/usr/bin/env python
import subprocess
import os

# where to store the output audio file, make sure the path exist (in this case, ~/temp)
# by default, this script stores them in: /home/$USER/temp/
outputDir = "/home/" + os.getlogin() + "/temp/"

# location of your ffmpeg installation
ffmpeg = "/usr/bin/ffmpeg"
ffprobe = "/usr/bin/ffprobe"

# get the resolve object (pre-injected when run from inside Resolve's Scripts menu)
resolve = bmd.scriptapp("Resolve")

project = resolve.GetProjectManager().GetCurrentProject()
timeline = project.GetCurrentTimeline()
mediaPool = project.GetMediaPool()

# the video item the playhead is currently on
video_item = timeline.GetCurrentVideoItem()
clipName = video_item.GetName()

# get the absolute file path of all the video clips in video track 1
track_items = timeline.GetItemsInTrack("video", 1)
full_file_path = None
for item in track_items.values():
    media_pool_item = item.GetMediaPoolItem()
    if media_pool_item != None:
        if clipName == media_pool_item.GetClipProperty("File Path").split("/")[-1]:
            full_file_path = media_pool_item.GetClipProperty("File Path")
            break
if full_file_path == None:
    print("Unable to get full file path of video")
    exit(1)

# work out source in/out of the visible portion, in frames
fps = float(project.GetSetting("timelineFrameRate"))
left_offset = video_item.GetLeftOffset()       # source frame where visible portion starts
visible_frames = video_item.GetDuration()      # number of frames visible on the timeline
start_sec = left_offset / fps
dur_sec = visible_frames / fps

# build output filename, encoding the source in/out so each trim caches separately
ext = clipName.split(".")[-1].lower()
video_container_list = ["mp4", "mov", "mkv", "m4a", "avi", "webm", "wmv"]
if ext not in video_container_list:
    print("Unknown video format")
    exit(1)
base = clipName.lower()[: -(len(ext) + 1)]      # strip ".ext"
outputClipName = f"{base}_{left_offset}-{left_offset + visible_frames}.wav"
outputPath = outputDir + outputClipName


def timecode_to_frames(timecode, fps):
    """Convert timecode string to frame count"""
    hours, minutes, seconds, frames = map(int, timecode.split(":"))
    return ((hours * 3600) + (minutes * 60) + seconds) * fps + frames


def remove_silent_audio_at_playhead():
    """Find the audio item that overlaps the current video item and delete it.

    Resolve on Linux imports a silent (uncodec'd) audio item alongside the
    video. We match by timeline position overlap and remove it so the
    converted WAV can take its place.
    """
    v_start = video_item.GetStart()
    v_end = video_item.GetEnd()

    audio_track_count = timeline.GetTrackCount("audio")
    to_delete = []
    for t in range(1, audio_track_count + 1):
        for a_item in timeline.GetItemsInTrack("audio", t).values():
            a_start = a_item.GetStart()
            a_end = a_item.GetEnd()
            # overlap test
            if a_start < v_end and a_end > v_start:
                to_delete.append(a_item)

    if to_delete:
        timeline.DeleteClips(to_delete)
        print(f"Removed {len(to_delete)} silent audio item(s)")
    else:
        print("No overlapping audio item found to remove")


def add_audio_clip_at_clip_start(media_pool_item, audio_track=1):
    # remember playhead so we can restore it afterward
    playhead_timecode = timeline.GetCurrentTimecode()

    # insert at the start of the video clip, regardless of playhead position
    clip_start_frame = video_item.GetStart()
    duration = media_pool_item.GetClipProperty("Duration")

    # Add to audio track (negative track numbers for audio)
    mediaPool.AppendToTimeline(
        [
            {
                "mediaPoolItem": media_pool_item,
                "startFrame": 0,
                "endFrame": duration,
                "trackIndex": -abs(audio_track),
                "recordFrame": clip_start_frame,
            }
        ]
    )

    # set playhead back to where it was
    timeline.SetCurrentTimecode(playhead_timecode)

    print(
        f"Added audio clip '{media_pool_item.GetClipProperty('Clip Name')}' "
        f"to track A{audio_track} at clip start (frame {clip_start_frame})"
    )
    return True


def buildFFmpegCommand():
    return [
        ffmpeg,
        "-n",
        "-ss", str(start_sec),   # seek to start of visible portion (before -i = fast & accurate)
        "-i", full_file_path,
        "-t", str(dur_sec),      # only the visible duration
        "-af", "apad",           # pad with silence so it exactly fills the trimmed window
        outputPath,
    ]


def runFFmpeg(commands):
    if subprocess.run(commands).returncode == 0:
        print("ffmpeg script ran successfully")
    else:
        print("Error running ffmpeg script")


# remove the silent audio that came in with the video clip
remove_silent_audio_at_playhead()

# if converted audio file already exists in outputDir, just import it
already_exists = outputClipName in os.listdir(outputDir)
if not already_exists:
    runFFmpeg(buildFFmpegCommand())

imported = mediaPool.ImportMedia([outputPath])
if imported:
    add_audio_clip_at_clip_start(imported[0], audio_track=1)
else:
    print("Import failed")
