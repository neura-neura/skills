---
name: video-subtitle-sync
description: Align an SRT file to subtitles visibly burned into a local video, correcting timing, duplicates, OCR errors, incomplete text, and spelling. Use when the user provides video and subtitle file paths for comparison.
---

# Video Subtitle Sync

Given a local video path and an SRT path, produce a corrected SRT whose text and timings match the captions burned into the video. The user normally only needs to provide those two paths. Infer the subtitle language from the files and audio/context; do not ask for it unless necessary.

## Workflow

1. Resolve both paths and confirm they exist. Preserve the source SRT; write the result beside it as `<stem>_corrected.srt` unless the user specified an output path. Write a concise `<stem>_subtitle_review.txt` alongside it for uncertain readings, material corrections, and coverage limitations.
2. Read this skill's `scripts/README.md` for local setup and run `scripts/inspect_subtitles.py` with both paths. The helper probes the video, reads SRT cues, samples at up to 2 frames per second, and performs local OCR on likely caption regions. Pass `--ocr-lang` for the video's installed Tesseract language packs when needed. It emits an OCR observations file and a cue-to-observation review table; it does not silently rewrite subtitle text.
3. Compare every SRT cue with video OCR observations over the full runtime. Use the OCR table to locate each cue's corresponding on-screen text and inspect the video at those times. For a long film, work chronologically in manageable batches, while maintaining cue and timestamp continuity. Review each cue, not merely a sample of SRT entries.
4. Inspect boundary frames at the nearest video frame before and after each cue's current start/end when timing is in doubt. The 2-fps scan is a locator, not proof of exact sub-second boundaries. Adjust cue edges only when the visible caption provides evidence. Do not apply one global offset unless the evidence supports a stable offset across the entire film.
5. Correct text against the image: remove OCR garbage, restore truncated words/lines, fix clear spelling and punctuation errors in the source language, and preserve capitalization, line breaks, speaker labels, and meaningful formatting where visible. Use context to distinguish OCR errors, but do not invent obscured or inaudible words. Mark genuinely unreadable portions as `[unreadable]` and record them in the review file.
6. Remove accidental duplicate cues and fragmented repeats by comparing normalized text and display intervals. Keep a repeated utterance when the video actually displays it again. Transform cues by timestamps/content, never by stale cue indexes after deletions or merges.
7. Merge or split cues only to match caption changes on screen. Preserve valid SRT numbering, timestamp syntax, chronological order, and intentional overlaps when they reflect the video.
8. Save a new UTF-8 SRT and review file. Re-open and structurally validate the output: cue numbering, timestamp parsing, positive durations, chronological ordering, accidental duplicates, obvious junk text, and video-duration bounds. Summarize changes and unresolved ambiguities to the user.

## Video inspection guidance

- Prefer local `ffprobe` and `ffmpeg` for metadata and frame extraction. Sample at no more than 2 fps for broad discovery on long videos; this bounds volume but can miss brief captions. Use focused, denser extraction around uncertain or short cues and inspect source-resolution boundary frames.
- Use a local OCR engine such as RapidOCR/EasyOCR/Tesseract on a cropped caption band. If captions move, resize, or use multiple lines, inspect full frames or multiple vertical bands rather than assuming a fixed crop. Preserve timestamps with each OCR observation.
- If the video contains a selectable subtitle stream, inspect it too, but treat the visible burned-in captions as the source of truth when they conflict.
- Keep all media processing local by default. Do not upload video/audio to a transcription service. If an external service would materially help resolve a phrase, explain what would be sent and ask first.
- Be accurate about coverage: a 2-fps scan is not frame-by-frame review. Do not claim every source frame was inspected unless it actually was. If tooling is unavailable, continue with available local video/UI inspection and clearly report the resulting coverage.

## Helper

See `scripts/README.md` for dependencies and invocation. The helper is an aid for indexing visible text and matching cues, not an authority on corrections. Visually verify uncertain readings and all proposed timing changes before delivering the SRT.

