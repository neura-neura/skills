# Local subtitle inspection helper

The helper samples video frames and OCRs likely subtitle regions to create a searchable index for manual, visual comparison. It never edits the source SRT.

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` on `PATH`
- Either Tesseract OCR on `PATH` with the video's language pack, or Python packages `rapidocr` and `Pillow`

Install packages in the Python environment used to run the helper:

```powershell
python -m pip install rapidocr Pillow
```

Check `ffmpeg -version` and `ffprobe -version` before starting. The helper writes outputs beside the SRT by default.

## Run

```powershell
python scripts/inspect_subtitles.py "D:\Movies\film.mkv" "D:\Movies\film.srt"
```

Optional flags:

- `--sample-fps 2`: broad sampling rate, capped at 2 fps by default; use lower rates for exceptionally long videos, then make focused checks around uncertain cues.
- `--output-dir PATH`: directory for helper artifacts.
- `--crop-bottom 0.35`: fraction of frame height to OCR from the bottom (default 0.35). Set to `1.0` if captions move or appear outside the lower band.

Outputs:

- `*_ocr.jsonl`: timestamped OCR observations and confidence values.
- `*_cue_matches.csv`: each SRT cue with candidate OCR observations ranked by text similarity and time proximity.
- `*_inspection.json`: video metadata, SRT parsing warnings, and run parameters.

Tesseract is preferred when available because it supports language-specific models (for example `spa` for Spanish). Use `--ocr-lang spa+eng` to select installed language packs. If Tesseract is unavailable, RapidOCR is used as a fallback; its recognition quality depends on its installed model and can be poor for some languages.

This helper is deliberately conservative: candidate OCR text is evidence to review, not an automatic replacement for visible captions. Compare each cue to its actual video frame and make corrections in a separate SRT.
