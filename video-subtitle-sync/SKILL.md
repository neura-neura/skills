---
name: video-subtitle-sync
description: Generate an SRT from subtitles burned into a local video, or align an existing SRT to those captions by correcting timing, duplicates, OCR errors, incomplete text, and spelling. Use when the user provides a local video path, with or without an SRT path.
---

# Video Subtitle Sync

Given a local video path, produce an SRT whose text and timings match captions burned into the video. If the user also provides an SRT path, synchronize and clean that file against the visible captions. If the user provides only a video path, assume there is no SRT and generate one from the visible captions. The user normally only needs to provide the path or paths. Infer the subtitle language from the captions and context; do not ask for it unless necessary.

## Workflow

1. Resolve the video path and, if supplied, the SRT path. Confirm every provided path exists. When an SRT was supplied, preserve it and write the result beside it as `<stem>_corrected.srt` unless the user specified an output path. When only a video was supplied, create `<video-stem>.srt` beside it (or use the requested output path). In both modes, write a concise `<video-stem>_subtitle_review.txt` alongside the output for uncertain readings, material corrections, and coverage limitations.
2. Read this skill's `scripts/README.md` for local setup. Run `scripts/inspect_subtitles.py` with the video path and the optional SRT path when one was supplied. The helper probes the video, reads SRT cues, samples at up to 2 frames per second, and performs local OCR on likely caption regions. Pass `--ocr-lang` for the video's installed Tesseract language packs when needed. It emits an OCR observations file and a cue-to-observation review table; it does not silently rewrite subtitle text.
3. In sync mode, compare every supplied SRT cue with video OCR observations over the full runtime; use the cue-match table to locate its visible counterpart. In generation mode, derive caption text and display intervals from timestamped OCR observations, consolidating repeated frame detections into continuous display intervals and splitting when the on-screen text changes. For a long film, work chronologically in manageable batches while maintaining timestamp continuity. Review the full runtime, not merely a sample of cues.
4. Inspect boundary frames at the nearest video frame before and after each cue's current start/end when timing is in doubt. The 2-fps scan is a locator, not proof of exact sub-second boundaries. Adjust cue edges only when the visible caption provides evidence. Do not apply one global offset unless the evidence supports a stable offset across the entire film.
5. Correct text against the image: remove OCR garbage, restore truncated words/lines, fix clear spelling and punctuation errors in the source language, and preserve capitalization, line breaks, speaker labels, and meaningful formatting where visible. Use context to distinguish OCR errors, but do not invent obscured or inaudible words. Mark genuinely unreadable portions as `[unreadable]` and record them in the review file.
6. Remove accidental duplicate cues and fragmented repeats by comparing normalized text and display intervals. Keep a repeated utterance when the video actually displays it again. Transform cues by timestamps/content, never by stale cue indexes after deletions or merges.
7. Merge or split cues only to match caption changes on screen. Preserve valid SRT numbering, timestamp syntax, chronological order, and intentional overlaps when they reflect the video.
8. Save the output as a UTF-8 SRT and write the review file. Re-open and structurally validate the output: cue numbering, timestamp parsing, positive durations, chronological ordering, accidental duplicates, obvious junk text, and video-duration bounds. Summarize changes and unresolved ambiguities to the user.

## Video inspection guidance

- Prefer local `ffprobe` and `ffmpeg` for metadata and frame extraction. Sample at no more than 2 fps for broad discovery on long videos; this bounds volume but can miss brief captions. Use focused, denser extraction around uncertain or short cues and inspect source-resolution boundary frames.
- Use a local OCR engine such as RapidOCR/EasyOCR/Tesseract on a cropped caption band. If captions move, resize, or use multiple lines, inspect full frames or multiple vertical bands rather than assuming a fixed crop. Preserve timestamps with each OCR observation.
- If the video contains a selectable subtitle stream, inspect it too, but treat the visible burned-in captions as the source of truth when they conflict.
- Keep all media processing local by default. Do not upload video/audio to a transcription service. If an external service would materially help resolve a phrase, explain what would be sent and ask first.
- Be accurate about coverage: a 2-fps scan is not frame-by-frame review. Do not claim every source frame was inspected unless it actually was. If tooling is unavailable, continue with available local video/UI inspection and clearly report the resulting coverage.

## Helper

See `scripts/README.md` for dependencies and invocation. The helper is an aid for indexing visible text and matching existing cues, not an SRT generator or authority on corrections. In video-only mode, use its timestamped observations as a locator and build the SRT after visually reviewing the frames. Visually verify uncertain readings and all proposed timing changes before delivering the SRT.
