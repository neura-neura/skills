# Local subtitle inspection helper

The helper samples video frames and OCRs likely subtitle regions to create a searchable index for manual, visual comparison. With no SRT argument it groups near-identical consecutive observations into provisional caption intervals; with an SRT argument it ranks observations against each cue. It never edits an SRT or claims provisional intervals are final; visually verify the caption text and boundaries.

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` on `PATH`
- Either Tesseract OCR on `PATH` with the video's language pack, or Python packages `rapidocr` and `Pillow`

Install packages in the Python environment used to run the helper:

```powershell
python -m pip install rapidocr Pillow
```

Check `ffmpeg -version` and `ffprobe -version` before starting. The helper writes inspection artifacts beside the SRT when supplied, or beside the video when running without an SRT.

## Run

```powershell
python scripts/inspect_subtitles.py "D:\Movies\film.mkv"
python scripts/inspect_subtitles.py "D:\Movies\film.mkv" "D:\Movies\film.srt"
```

Optional flags:

- `--sample-fps 2`: broad sampling rate, capped at 2 fps by default; use lower rates for exceptionally long videos, then make focused checks around uncertain cues.
- `--output-dir PATH`: directory for helper artifacts.
- `--crop-bottom 0.35`: fraction of frame height to OCR from the bottom (default 0.35). Set to `1.0` if captions move or appear outside the lower band.

Outputs:

- `*_ocr.jsonl`: timestamped OCR observations and confidence values.
- `*_cue_matches.csv`: when an SRT is supplied, each cue with candidate OCR observations ranked by text similarity and time proximity.
- `*_caption_candidates.csv`: when no SRT is supplied, OCR text grouped into provisional display intervals with estimated start/end times. Verify these against the video before writing the final SRT.
- `*_inspection.json`: video metadata, SRT parsing warnings, and run parameters.

Tesseract is preferred when available because it supports language-specific models (for example `spa` for Spanish). Use `--ocr-lang spa+eng` to select installed language packs. If Tesseract is unavailable, RapidOCR is used as a fallback; its recognition quality depends on its installed model and can be poor for some languages.

In video-only mode, visually review timestamped OCR observations and assemble cues with start/end times matching when each caption appears. In sync mode, compare each cue to its actual video frame and make corrections in a separate SRT. OCR output is evidence to review, not an automatic replacement for visible captions.
