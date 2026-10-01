# Translation and combined subtitle files

Use this guide only after the source-language SRT is complete and reviewed.

## Translation

- Translate all cue text into each requested target language.
- Keep the original cue numbering, order, timestamps, speaker labels, and intentional line boundaries aligned with the source.
- Preserve names, honorifics, terminology, tone, and meaning; translate naturally rather than word-for-word.
- Keep each language in its own UTF-8 SRT. Use language suffixes such as `_en.srt`, `_zh.srt`, or clear full language names. Never overwrite the source or another target file.
- Read the completed translation as a whole for consistency and verify it still has the same cue count and timestamps.

## Combined bilingual or multilingual SRT

- Pair translations by cue identity and source timing. Each paired cue remains a single SRT block with the same start and end timestamps as the reviewed source cue.
- Put languages in the user's requested order. Each language gets a separate text line within that cue; for example Chinese on the first line and Spanish on the second.
- Preserve intended line breaks within each language while separating language lines clearly. Do not put language names in the subtitle text unless requested.
- If a target language has no text for a source cue, preserve the source line and leave the other language line empty only when this reflects the meaning (for example a non-speech marker); otherwise record the issue and resolve it. Do not silently drop a cue.
- Validate numbering, timestamp syntax, chronology, positive durations, cue count, and the text order in the combined file. Use a descriptive filename such as `_zh-es_dual.srt`.

## Asking after source analysis

Finish the source-language SRT first. If the user has not already said what they want, ask once whether they want translation, a combined file, or both. Ask for target language(s), and for a combined file ask the line order (first/on top, then second/bottom). Treat “neither” as a valid answer and do not ask again for a choice they already specified.
