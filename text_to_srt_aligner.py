import argparse
import difflib
import re
from pathlib import Path

import torch
import whisper


def normalize_text(text: str) -> str:
    """
    テキスト照合用の正規化。
    空白・記号を落として、かな/漢字/英数字をなるべく残す。
    """
    text = text.lower()
    text = text.replace("　", "")
    text = re.sub(r"\s+", "", text)

    # 日本語・英数字以外の記号をだいたい除去
    text = re.sub(
        r"[、。．，,.!?！？…・:：;；'\"“”‘’（）()\[\]【】『』「」〈〉《》<>\-―ー~〜♪♫／/\\|]",
        "",
        text,
    )
    return text


def srt_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    ms = int(round(seconds * 1000))
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1000
    ms %= 1000
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def read_text_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8-sig")
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # SUNOタグなど、角括弧だけの構成タグを字幕に出したくない場合は飛ばす
        if re.fullmatch(r"\[.*?\]", line):
            continue
        lines.append(line)
    return lines


def build_transcript_chars(segments):
    """
    Whisper segments から、
    正規化文字列 transcript_norm と、
    各文字のおおよその時刻 char_times を作る。
    """
    transcript_chars = []
    char_times = []

    for seg in segments:
        raw_text = seg.get("text", "")
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start + 0.1))

        norm = normalize_text(raw_text)
        if not norm:
            continue

        n = len(norm)
        duration = max(end - start, 0.05)

        for i, ch in enumerate(norm):
            if n == 1:
                t = start
            else:
                t = start + duration * (i / (n - 1))
            transcript_chars.append(ch)
            char_times.append(t)

    return "".join(transcript_chars), char_times


def build_source_text_chars(lines: list[str]):
    """
    入力テキスト行ごとの正規化文字範囲を作る。
    """
    chars = []
    ranges = []

    pos = 0
    for line in lines:
        norm = normalize_text(line)
        start = pos
        chars.extend(norm)
        pos += len(norm)
        end = pos
        ranges.append((start, end))

    return "".join(chars), ranges


def align_lines_to_times(lines, text_norm, text_ranges, trans_norm, char_times):
    """
    difflibで入力テキスト全文とWhisper全文を照合し、
    各テキスト行に対応するWhisper側の文字位置を集める。
    """
    matcher = difflib.SequenceMatcher(None, text_norm, trans_norm, autojunk=False)
    blocks = matcher.get_matching_blocks()

    text_to_trans_positions = [[] for _ in lines]

    # source text char index -> line index
    text_index_to_line = {}
    for line_idx, (a, b) in enumerate(text_ranges):
        for p in range(a, b):
            text_index_to_line[p] = line_idx

    matched_chars = 0

    for block in blocks:
        if block.size <= 0:
            continue

        for offset in range(block.size):
            text_pos = block.a + offset
            trans_pos = block.b + offset

            line_idx = text_index_to_line.get(text_pos)
            if line_idx is not None and trans_pos < len(char_times):
                text_to_trans_positions[line_idx].append(trans_pos)
                matched_chars += 1

    line_times = []

    for positions in text_to_trans_positions:
        if positions:
            a = min(positions)
            b = max(positions)
            start = char_times[a]
            end = char_times[b] + 0.35
            line_times.append([start, end, True])
        else:
            line_times.append([None, None, False])

    match_rate = matched_chars / max(len(text_norm), 1)
    return line_times, match_rate


def fill_missing_times(line_times, total_start, total_end, default_line_duration=1.8):
    """
    一致しなかった行の時刻を、前後の既知タイムから補間する。

    default_line_duration は、既知タイムがない箇所や前後の隙間が足りない箇所で
    未一致行に与える標準的な表示時間。速い曲・遅い朗読などに合わせて調整できる。
    """
    n = len(line_times)
    default_line_duration = max(float(default_line_duration), 0.05)

    known = [i for i, t in enumerate(line_times) if t[2]]

    if not known:
        # 全滅した場合は、default_line_duration を基準に全体へ均等配置
        dur = max(total_end - total_start, n * default_line_duration)
        step = dur / max(n, 1)
        for i in range(n):
            line_times[i][0] = total_start + i * step
            line_times[i][1] = total_start + (i + 1) * step
            line_times[i][2] = False
        return line_times

    # 先頭側を補間
    first = known[0]
    for i in range(first - 1, -1, -1):
        line_times[i][1] = line_times[i + 1][0]
        line_times[i][0] = max(total_start, line_times[i][1] - default_line_duration)

    # 間を補間
    for left, right in zip(known, known[1:]):
        gap = right - left
        if gap <= 1:
            continue

        start = line_times[left][1]
        end = line_times[right][0]
        span = max(end - start, gap * default_line_duration)
        step = span / gap

        for j in range(1, gap):
            idx = left + j
            line_times[idx][0] = start + (j - 1) * step
            line_times[idx][1] = start + j * step

    # 末尾側を補間
    last = known[-1]
    for i in range(last + 1, n):
        line_times[i][0] = line_times[i - 1][1]
        line_times[i][1] = min(total_end, line_times[i][0] + default_line_duration)

    return line_times

def enforce_timing(line_times, min_duration=0.8, gap=0.03):
    """
    SRTとして破綻しないように、
    単調増加・最小表示時間を保証する。
    """
    prev_end = 0.0

    for t in line_times:
        start, end, matched = t

        if start is None:
            start = prev_end + gap
        if end is None:
            end = start + min_duration

        start = max(start, prev_end + gap)
        end = max(end, start + min_duration)

        t[0] = start
        t[1] = end
        prev_end = end

    return line_times


def write_srt(path: Path, lines, line_times, offset=0.0):
    out = []

    for i, (line, timing) in enumerate(zip(lines, line_times), start=1):
        start = timing[0] + offset
        end = timing[1] + offset

        out.append(str(i))
        out.append(f"{srt_timestamp(start)} --> {srt_timestamp(end)}")
        out.append(line)
        out.append("")

    path.write_text("\n".join(out), encoding="utf-8-sig")


def main():
    parser = argparse.ArgumentParser(
        description="Generate .srt subtitles by aligning an audio file with an existing text file using Whisper."
    )
    parser.add_argument("--audio", required=True, help="Audio file: wav/mp3/m4a etc.")
    parser.add_argument("--text", help="Source text file to align: script/lyrics/transcript etc.")
    parser.add_argument("--lyrics", help="Deprecated alias for --text. Kept for backward compatibility.")
    parser.add_argument("--out", required=True, help="Output .srt path.")
    parser.add_argument("--model", default="small", help="Whisper model: tiny/base/small/medium/large")
    parser.add_argument("--language", default="ja", help="Language code. Japanese = ja")
    parser.add_argument("--offset", type=float, default=0.0, help="Timing offset in seconds.")
    parser.add_argument("--min-duration", type=float, default=0.9, help="Minimum subtitle duration.")
    parser.add_argument("--default-line-duration", type=float, default=1.8, help="Default duration in seconds for unmatched subtitle lines.")
    args = parser.parse_args()

    audio_path = Path(args.audio)
    text_arg = args.text or args.lyrics
    if not text_arg:
        parser.error("either --text or --lyrics is required")
    if args.text and args.lyrics:
        parser.error("use either --text or --lyrics, not both")

    text_path = Path(text_arg)
    out_path = Path(args.out)

    lines = read_text_lines(text_path)
    if not lines:
        raise RuntimeError("テキストTXTに有効な行がありません。")

    print(f"[info] text lines: {len(lines)}")
    print(f"[info] loading Whisper model: {args.model}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[info] device: {device}")

    model = whisper.load_model(args.model, device=device)

    print("[info] transcribing audio...")
    result = model.transcribe(
        str(audio_path),
        language=args.language,
        fp16=(device == "cuda"),
        verbose=False,
    )

    segments = result.get("segments", [])
    if not segments:
        raise RuntimeError("Whisperのsegmentsが空です。音声を認識できていない可能性があります。")

    total_start = float(segments[0].get("start", 0.0))
    total_end = float(
        segments[-1].get("end", total_start + len(lines) * args.default_line_duration)
    )

    trans_norm, char_times = build_transcript_chars(segments)
    text_norm, text_ranges = build_source_text_chars(lines)

    print(f"[info] normalized text chars: {len(text_norm)}")
    print(f"[info] normalized transcript chars: {len(trans_norm)}")

    if not trans_norm:
        raise RuntimeError("Whisper文字起こしの正規化結果が空です。")

    line_times, match_rate = align_lines_to_times(
        lines, text_norm, text_ranges, trans_norm, char_times
    )

    print(f"[info] rough match rate: {match_rate:.2%}")

    line_times = fill_missing_times(
        line_times,
        total_start,
        total_end,
        default_line_duration=args.default_line_duration,
    )
    line_times = enforce_timing(line_times, min_duration=args.min_duration)

    write_srt(out_path, lines, line_times, offset=args.offset)

    matched_count = sum(1 for t in line_times if t[2])
    print(f"[done] wrote: {out_path}")
    print(f"[info] matched lines: {matched_count}/{len(lines)}")

    if match_rate < 0.25:
        print("[warn] 一致率が低いです。入力テキストとWhisper文字起こしがかなり違う可能性があります。")
        print("[warn] modelを medium/large にする、テキスト表記を音源に近づける、行を短めにする、などを試してください。")


if __name__ == "__main__":
    main()