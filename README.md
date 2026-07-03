# Text-to-SRT-Aligner

A small Python script that generates a draft SRT subtitle file from an audio file and a plain text file.

It uses Whisper to transcribe the audio, compares the transcription with the provided text, and estimates rough start/end timings for each text line.

This is not a perfect automatic alignment tool. It is intended to create a draft subtitle file that you can manually adjust in YouTube Studio, Subtitle Edit, Aegisub, or other subtitle editors.

The tool is language-agnostic. It can be used with any language supported by Whisper, as long as the provided text closely matches the spoken or sung audio.

---

音声ファイルとテキストファイルから、YouTubeや動画編集ソフトなどで使用できるSRT字幕ファイルの下書きを生成するミニPythonスクリプトです。

Whisperで音声を文字起こしし、その認識結果と入力テキストを照合して、各行のおおまかな開始・終了時刻を推定します。

完全な自動同期ではありません。生成後にYouTube Studio、Subtitle Edit、Aegisubなどで手動確認・修正する前提の下書き生成ツールです。（でも、たぶん無から生成するよりは全然楽。）

Whisperが対応している言語であれば利用できます。精度はWhisperの認識結果と、入力テキストが実際の音声内容にどれだけ近いかに左右されます。

ChatGPTと一緒に作りました。

## Requirements

- Python 3.10 or later
- ffmpeg
- openai-whisper
- torch

## Install

このリポジトリをダウンロード、または clone します。

```bash
git clone https://github.com/NONAMEmurmur/Text-to-SRT-Aligner.git
cd Text-to-SRT-Aligner
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

音声ファイルとテキストファイルを用意します。

例：

```txt
audio.wav
text.txt
```

基本コマンド：

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model small --language ja
```

生成されるファイル：

```txt
output.srt
```

この `.srt` ファイルは、YouTube Studio の字幕ファイルとしてアップロードしたり、動画編集ソフトで読み込んだりできます。

For backward compatibility, `--lyrics` is also supported.

```bash
python text_to_srt_aligner.py --audio audio.wav --lyrics text.txt --out output.srt --model small --language ja
```

## Options

### Whisperモデルを変える

軽め：

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model base --language ja
```

標準：

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model small --language ja
```

精度重視：

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model medium --language ja
```

さらに精度重視：

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model large --language ja
```

モデルが大きいほど精度が上がる可能性がありますが、処理は重くなります。

### Language

Whisperが対応している言語を指定できます。

日本語：

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model small --language ja
```

英語：

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model small --language en
```

言語指定を省略したい場合は、スクリプト側の既定値が使われます。

## Timing offset

字幕が全体的に早い、または遅い場合は `--offset` を使います。

字幕を 0.5 秒遅らせる：

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model small --language ja --offset 0.5
```

字幕を 0.3 秒早める：

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model small --language ja --offset -0.3
```

## Minimum subtitle duration

字幕1行あたりの最小表示時間を変えたい場合は `--min-duration` を使います。

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model small --language ja --min-duration 1.2
```

## Default line duration

Whisperの認識結果とうまく一致しなかった行には、前後の時刻から補間したタイミングが割り当てられます。

その際に使う1行あたりの仮の長さを変えたい場合は `--default-line-duration` を使います。

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model small --language ja --default-line-duration 1.2
```

速い発話や速い曲では短めに、ゆっくりした朗読やナレーションでは長めにすると調整しやすくなる場合があります。

例：

```bash
# fast speech / fast song
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --default-line-duration 1.2

# slow narration
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --default-line-duration 2.5
```

## Text TXT format

テキストファイルは、字幕にしたい単位で1行ずつ書いてください。

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

また、以下のような角括弧だけの行は、構成タグとして扱い、字幕から除外します。

```txt
[Verse]
[Chorus]
[Outro]
```

## Notes

- このツールは字幕の下書きを作るためのものです。公開前に手動確認・修正することをおすすめします。
- 精度はWhisperの認識結果と、入力テキストが実際の音声内容にどれだけ近いかに左右されます。
- 早口、重なった声、コーラス、強いエフェクトがある音源ではズレやすくなります。
- 入力テキストの行分けが細かすぎる、または長すぎる場合もズレることがあります。
- Whisperが対応している言語であれば利用できます。
- 処理する音源・テキストの権利には注意してください。

## Troubleshooting

### `No such file or directory` と出る

指定した音声ファイルやテキストファイルが見つかっていません。

ファイル名と場所を確認してください。

```bash
python text_to_srt_aligner.py --audio audio.wav --text text.txt --out output.srt --model small --language ja
```

空白や日本語を含むファイル名を使う場合は、引用符で囲んでください。

```bash
python text_to_srt_aligner.py --audio "my audio.wav" --text "原稿.txt" --out "output.srt" --model small --language ja
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
- 入力テキストを実際の音声内容に近い表記にする
- 入力テキストの行分けを調整する
- `--offset` で全体のズレを補正する
- `--min-duration` を調整する
- `--default-line-duration` を調整する
- YouTube Studio、Subtitle Edit、Aegisubなどで手動修正する

### 一致率が低いという警告が出る

Whisperの文字起こし結果と、入力テキストの内容が大きく違っている可能性があります。

以下を確認してください。

- 音声ファイルとテキストファイルの内容が対応しているか
- `--language` が正しいか
- Whisperモデルが小さすぎないか
- テキストに読み上げられていない行が多く含まれていないか
- 音声に入力テキスト以外の発話やコーラスが多く含まれていないか

## Credits

This script was created with assistance from ChatGPT.

It was made after experimenting with jossieb/lyrics-sync, but it does not copy code from that repository.

This is a simplified standalone script focused on generating draft SRT files by aligning existing text with audio.

## License

MIT License
