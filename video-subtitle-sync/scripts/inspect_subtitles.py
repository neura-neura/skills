#!/usr/bin/env python3
"""Index likely burned-in captions and rank nearby OCR observations for SRT cues."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

TIME_RE = re.compile(r"(\d{2,}):(\d{2}):(\d{2})[,.](\d{3})")


@dataclass
class Cue:
    number: int
    start: float
    end: float
    text: str


def parse_time(value: str) -> float:
    match = TIME_RE.fullmatch(value.strip())
    if not match:
        raise ValueError(f"invalid SRT timestamp: {value!r}")
    h, m, s, ms = (int(part) for part in match.groups())
    if m >= 60 or s >= 60:
        raise ValueError(f"out-of-range SRT timestamp: {value!r}")
    return h * 3600 + m * 60 + s + ms / 1000


def decode_srt(path: Path) -> tuple[str, str]:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("Could not decode the SRT text")


def parse_srt(text: str) -> tuple[list[Cue], list[str]]:
    cues: list[Cue] = []
    warnings: list[str] = []
    blocks = re.split(r"\r?\n\s*\r?\n", text.strip())
    for block_index, block in enumerate(blocks, 1):
        lines = block.splitlines()
        if not lines:
            continue
        timing_i = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if timing_i is None:
            warnings.append(f"Block {block_index}: no timing line; skipped")
            continue
        timing = lines[timing_i].split("-->")
        if len(timing) != 2:
            warnings.append(f"Block {block_index}: malformed timing line; skipped")
            continue
        try:
            start = parse_time(timing[0])
            # Ignore optional SRT positioning tokens after the end timestamp.
            end_token = timing[1].strip().split()[0]
            end = parse_time(end_token)
        except (ValueError, IndexError) as error:
            warnings.append(f"Block {block_index}: {error}; skipped")
            continue
        body = "\n".join(lines[timing_i + 1 :]).strip()
        try:
            number = int(lines[0].strip())
        except ValueError:
            number = block_index
            warnings.append(f"Block {block_index}: nonnumeric cue number; inferred {number}")
        if not body:
            warnings.append(f"Cue {number}: empty text")
        if end <= start:
            warnings.append(f"Cue {number}: nonpositive duration")
        cues.append(Cue(number, start, end, body))
    return cues, warnings


def run_probe(video: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate",
        "-of", "json", str(video),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def normalize(value: str) -> str:
    value = value.casefold()
    value = re.sub(r"<[^>]*>", " ", value)
    return " ".join(re.findall(r"[\wáéíóúüñç]+", value, flags=re.UNICODE))


def similarity(left: str, right: str) -> float:
    # RapidFuzz is optional; the fallback keeps the script dependency-light.
    try:
        from rapidfuzz.fuzz import ratio  # type: ignore[import-not-found]

        return ratio(left, right) / 100.0
    except ImportError:
        from difflib import SequenceMatcher

        return SequenceMatcher(None, left, right).ratio()


def ocr_frames(
    video: Path, duration: float, fps: float, crop_bottom: float, ocr_lang: str
) -> list[dict[str, Any]]:
    use_tesseract = shutil.which("tesseract") is not None
    if not use_tesseract:
        try:
            from PIL import Image  # type: ignore[import-not-found]
            from rapidocr import RapidOCR  # type: ignore[import-not-found]
        except ImportError as error:
            raise RuntimeError(
                "No OCR engine found. Install Tesseract with a language pack or install "
                "rapidocr and Pillow; see scripts/README.md."
            ) from error
        engine = RapidOCR()
    dimension_probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height", "-of", "json", str(video)],
        check=True, capture_output=True, text=True,
    )
    stream = json.loads(dimension_probe.stdout).get("streams", [{}])[0]
    width, height = int(stream["width"]), int(stream["height"])
    interval = 1.0 / fps
    observations: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="subtitle_sync_") as temp_dir:
        frames_pattern = str(Path(temp_dir) / "frame_%08d.jpg")
        # fps filter with start_number 0 makes output indices map directly to sample time.
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video),
            "-vf", f"fps={fps},crop=iw:ih*{crop_bottom}:0:ih*(1-{crop_bottom})",
            "-q:v", "2", "-start_number", "0", frames_pattern,
        ]
        subprocess.run(command, check=True, capture_output=True)
        frame_paths = sorted(Path(temp_dir).glob("frame_*.jpg"))
        for index, frame_path in enumerate(frame_paths):
            t = index * interval
            parsed: list[tuple[str, float]] = []
            if use_tesseract:
                result = subprocess.run(
                    ["tesseract", str(frame_path), "stdout", "-l", ocr_lang, "tsv"],
                    capture_output=True, text=True,
                )
                if result.returncode:
                    raise RuntimeError(
                        f"Tesseract failed ({result.returncode}): {result.stderr.strip()}"
                    )
                reader = csv.DictReader(result.stdout.splitlines(), delimiter="\t")
                for row in reader:
                    text = (row.get("text") or "").strip()
                    try:
                        confidence = max(0.0, float(row.get("conf", "-1")) / 100.0)
                    except ValueError:
                        confidence = 0.0
                    if text and confidence > 0:
                        parsed.append((text, confidence))
            else:
                from PIL import Image

                with Image.open(frame_path) as frame:
                    result = engine(frame.convert("RGB"))
                rows = result[0] if isinstance(result, tuple) else getattr(result, "boxes", None)
                if rows is not None:
                    for row in rows:
                        if isinstance(row, (tuple, list)) and len(row) >= 3:
                            parsed.append((str(row[1]), float(row[2])))
            if parsed:
                observations.append({
                    "time": round(t, 3),
                    "text": "\n".join(text for text, _ in parsed),
                    "confidence": round(sum(score for _, score in parsed) / len(parsed), 4),
                })
    return observations


def rank_matches(cues: list[Cue], observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_observations = [normalize(str(item["text"])) for item in observations]
    rows: list[dict[str, Any]] = []
    for cue in cues:
        cue_text = normalize(cue.text)
        if not cue_text:
            continue
        midpoint = (cue.start + cue.end) / 2
        candidates: list[tuple[float, float, dict[str, Any]]] = []
        for obs, obs_text in zip(observations, normalized_observations):
            obs_time = float(obs["time"])
            temporal_distance = 0.0 if cue.start - 0.5 <= obs_time <= cue.end + 0.5 else min(
                abs(obs_time - cue.start), abs(obs_time - cue.end)
            )
            # Limit the broad candidate list; long-running unrelated matches are noisy.
            if temporal_distance > max(8.0, cue.end - cue.start + 4.0):
                continue
            text_score = similarity(cue_text, obs_text)
            proximity = math.exp(-temporal_distance / 8.0)
            combined = 0.85 * text_score + 0.15 * proximity
            candidates.append((combined, abs(obs_time - midpoint), obs))
        candidates.sort(key=lambda item: (-item[0], item[1]))
        for rank, (combined, _, obs) in enumerate(candidates[:5], 1):
            rows.append({
                "cue_number": cue.number,
                "cue_start": f"{cue.start:.3f}",
                "cue_end": f"{cue.end:.3f}",
                "cue_text": cue.text.replace("\n", " | "),
                "rank": rank,
                "ocr_time": f"{float(obs['time']):.3f}",
                "ocr_text": str(obs["text"]).replace("\n", " | "),
                "ocr_confidence": obs.get("confidence", ""),
                "text_similarity": f"{similarity(cue_text, normalize(str(obs['text']))):.4f}",
                "combined_score": f"{combined:.4f}",
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("srt", type=Path)
    parser.add_argument("--sample-fps", type=float, default=2.0)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--crop-bottom", type=float, default=0.35)
    parser.add_argument("--ocr-lang", default="eng", help="Tesseract language(s), e.g. spa+eng")
    args = parser.parse_args()
    video = args.video.expanduser().resolve()
    srt = args.srt.expanduser().resolve()
    output_dir = (args.output_dir or srt.parent).expanduser().resolve()

    if not video.is_file() or not srt.is_file():
        parser.error("video and SRT paths must both point to existing files")
    if not 0 < args.sample_fps <= 2:
        parser.error("--sample-fps must be greater than 0 and no more than 2")
    if not 0 < args.crop_bottom <= 1:
        parser.error("--crop-bottom must be greater than 0 and no more than 1")
    missing = [binary for binary in ("ffprobe", "ffmpeg") if not shutil.which(binary)]
    if missing:
        parser.error(f"missing from PATH: {', '.join(missing)}; install FFmpeg and retry")

    raw_srt, encoding = decode_srt(srt)
    cues, warnings = parse_srt(raw_srt)
    if not cues:
        parser.error("No valid SRT cues were found")
    try:
        metadata = run_probe(video)
        duration = float(metadata.get("format", {}).get("duration", 0))
        if duration <= 0:
            raise RuntimeError("Video duration is missing or invalid")
        observations = ocr_frames(video, duration, args.sample_fps, args.crop_bottom, args.ocr_lang)
    except (subprocess.CalledProcessError, RuntimeError) as error:
        detail = getattr(error, "stderr", None)
        if isinstance(detail, bytes):
            detail = detail.decode(errors="replace")
        print(f"error: {error}{': ' + detail if detail else ''}", file=sys.stderr)
        return 2

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = srt.stem
    observations_path = output_dir / f"{stem}_ocr.jsonl"
    matches_path = output_dir / f"{stem}_cue_matches.csv"
    inspection_path = output_dir / f"{stem}_inspection.json"
    with observations_path.open("w", encoding="utf-8", newline="\n") as stream:
        for observation in observations:
            stream.write(json.dumps(observation, ensure_ascii=False) + "\n")

    matches = rank_matches(cues, observations)
    fieldnames = list(matches[0]) if matches else [
        "cue_number", "cue_start", "cue_end", "cue_text", "rank", "ocr_time",
        "ocr_text", "ocr_confidence", "text_similarity", "combined_score",
    ]
    with matches_path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)

    inspection = {
        "video": str(video), "srt": str(srt), "srt_encoding": encoding,
        "duration_seconds": duration, "video_metadata": metadata,
        "cue_count": len(cues), "ocr_observation_count": len(observations),
        "sample_fps": args.sample_fps, "crop_bottom_fraction": args.crop_bottom,
        "ocr_engine": "tesseract" if shutil.which("tesseract") else "rapidocr",
        "ocr_language": args.ocr_lang if shutil.which("tesseract") else None,
        "warnings": warnings,
        "outputs": {
            "ocr_jsonl": str(observations_path),
            "cue_matches_csv": str(matches_path),
        },
        "note": "OCR candidates need visual verification; scan samples are not frame-by-frame review.",
    }
    inspection_path.write_text(json.dumps(inspection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Indexed {len(observations)} OCR observations for {len(cues)} cues.")
    print(f"OCR observations: {observations_path}")
    print(f"Cue candidates:   {matches_path}")
    print(f"Inspection info:  {inspection_path}")
    print("Visually verify captions and boundaries before editing the SRT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
