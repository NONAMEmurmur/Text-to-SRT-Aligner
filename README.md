# auto_srt_from_lyrics

A small Python script that generates a draft SRT subtitle file from an audio file and a lyrics TXT file.

It uses Whisper to transcribe the audio, compares the transcription with the provided lyrics, and estimates rough start/end timings for each lyric line.

This is not a perfect automatic alignment tool. It is intended to create a draft subtitle file that you can manually adjust in YouTube Studio, Subtitle Edit, Aegisub, or other subtitle editors.

---

音声ファイルと歌詞TXTから、YouTubeや動画編集ソフトなどで使用できるSRT字幕ファイルの下書きを生成するミニPythonスクリプトです。

Whisperで音声を文字起こしし、その認識結果と元の歌詞TXTを照合して、各歌詞行のおおまかな開始・終了時刻を推定します。

完全な自動同期ではありません。生成後にYouTube Studio、Subtitle Edit、Aegisubなどで手動確認・修正する前提の下書き生成ツールです。（でも、たぶん無から生成するよりは全然楽。）

jossieb/lyrics-sync に触発されて、ChatGPTと一緒に作りました。

## Requirements

- Python 3.10 or later
- ffmpeg
- openai-whisper
- torch

## Install

このリポジトリをダウンロード、または clone します。

```bash
git clone https://github.com/NONAMEmurmur/TXT-to-SRT.git
cd TXT-to-SRT
```

仮想環境を作成して有効化します。

### Windows / PowerShell

```powershell
py -3 -m venv venv
venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements.txt
```

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -U pip
pip install -r requirements.txt
```

ffmpeg も必要です。事前にインストールして、コマンドラインから使える状態にしてください。

確認：

```bash
ffmpeg -version
```

## Usage

音声ファイルと歌詞TXTを用意します。

例：

```txt
song.wav
lyrics.txt
```

基本コマンド：

```bash
python auto_srt_from_lyrics.py --audio song.wav --lyrics lyrics.txt --out song.srt --model small --language ja
```

生成されるファイル：

```txt
song.srt
```

この `.srt` ファイルは、YouTube Studio の字幕ファイルとしてアップロードしたり、動画編集ソフトで読み込んだりできます。

## Options

### Whisperモデルを変える

軽め：

```bash
python auto_srt_from_lyrics.py --audio song.wav --lyrics lyrics.txt --out song.srt --model base --language ja
```

標準：

```bash
python auto_srt_from_lyrics.py --audio song.wav --lyrics lyrics.txt --out song.srt --model small --language ja
```

精度重視：

```bash
python auto_srt_from_lyrics.py --audio song.wav --lyrics lyrics.txt --out song.srt --model medium --language ja
```

さらに精度重視：

```bash
python auto_srt_from_lyrics.py --audio song.wav --lyrics lyrics.txt --out song.srt --model large --language ja
```

モデルが大きいほど精度が上がる可能性がありますが、処理は重くなります。

## Timing offset

字幕が全体的に早い、または遅い場合は `--offset` を使います。

字幕を 0.5 秒遅らせる：

```bash
python auto_srt_from_lyrics.py --audio song.wav --lyrics lyrics.txt --out song.srt --model small --language ja --offset 0.5
```

字幕を 0.3 秒早める：

```bash
python auto_srt_from_lyrics.py --audio song.wav --lyrics lyrics.txt --out song.srt --model small --language ja --offset -0.3
```

## Minimum subtitle duration

字幕1行あたりの最小表示時間を変えたい場合は `--min-duration` を使います。

```bash
python auto_srt_from_lyrics.py --audio song.wav --lyrics lyrics.txt --out song.srt --model small --language ja --min-duration 1.2
```

## Lyrics TXT format

歌詞TXTは、字幕にしたい単位で1行ずつ書いてください。

例：

```txt
誰か、手を取って。
この沈んでいる気持ちを
引き上げてくれるだけでいいの。
必要なものはなんでもある。
でも、気持ちだけが沈み込んじゃって
滅茶苦茶なの。
```

空行は無視されます。

また、以下のような角括弧だけの行は、SUNOなどの構成タグとして扱い、字幕から除外します。

```txt
[Verse]
[Chorus]
[Outro]
```

## Notes

- このツールは字幕の下書きを作るためのものです。公開前に手動確認・修正することをおすすめします。
- 精度はWhisperの認識結果と、歌詞TXTが実際の歌唱にどれだけ近いかに左右されます。
- 早口、重なった声、コーラス、強いエフェクトがある音源ではズレやすくなります。
- 歌詞TXTの行分けが細かすぎる、または長すぎる場合もズレることがあります。
- 日本語歌詞向けに作っていますが、`--language en` などを指定すれば他言語でも試せます。
- 処理する音源・歌詞の権利には注意してください。

## Troubleshooting

### `No such file or directory` と出る

指定した音声ファイルや歌詞TXTが見つかっていません。

ファイル名と場所を確認してください。

```bash
python auto_srt_from_lyrics.py --audio song.wav --lyrics lyrics.txt --out song.srt --model small --language ja
```

空白や日本語を含むファイル名を使う場合は、引用符で囲んでください。

```bash
python auto_srt_from_lyrics.py --audio "my song.wav" --lyrics "歌詞.txt" --out "song.srt" --model small --language ja
```

### `ffmpeg` が見つからない

ffmpeg がインストールされていないか、PATH が通っていません。

確認：

```bash
ffmpeg -version
```

### 字幕がかなりズレる

以下を試してください。

- Whisperモデルを `medium` や `large` にする
- 歌詞TXTを実際の歌唱に近い表記にする
- 歌詞の行分けを調整する
- `--offset` で全体のズレを補正する
- YouTube Studio、Subtitle Edit、Aegisubなどで手動修正する

## Credits

This script was created with assistance from ChatGPT.

It was made after experimenting with jossieb/lyrics-sync, but it does not copy code from that repository.

This is a simplified standalone script focused on generating draft SRT files from audio and lyrics text.

## License

MIT License