# PDF Text Extractor with Auto OCR

![App Screenshot](https://user-images.githubusercontent.com/あなたのユーザーID/あなたのリポジトリID/....)  <!-- TODO: あとでアプリのスクリーンショットに差し替えてください -->

PDFからテキストを抽出するStreamlit製のWebアプリケーションです。
通常のテキスト抽出を試み、文字がほとんど含まれていない場合（スキャンされた画像PDFなど）は、自動的にOCR（光学的文字認識）処理に切り替えて文字を読み取ります。

A Streamlit web application to extract text from PDF files. It first attempts direct text extraction and automatically switches to OCR processing for scanned PDFs that do not have embedded text.

**[>> アプリを試す (Demo App)](https://あなたのアプリのURL.streamlit.app/)** <!-- TODO: デプロイ後にURLをここに貼ってください -->

---

## :sparkles: 主な機能 (Features)

- **自動OCR切り替え (Automatic OCR Fallback):** テキストが埋め込まれていないPDFを自動で判別し、OCR処理を実行します。
- **柔軟な設定 (Flexible Configuration):**
    - OCR言語（日本語、英語など複数指定可）
    - OCRの解像度（DPI）
    - OCRへ切り替える文字数の閾値
- **複数ファイル対応 (Multi-File Upload):** 一度に複数のPDFファイルをアップロードして処理できます。
- **レイアウト保持オプション (Layout Preservation):** 文章の段組やカラム構造をなるべく維持してテキストを抽出するモードを選択できます。
- **ダウンロード機能 (Downloadable Output):** 抽出した全文を `.txt` ファイルとしてダウンロードできます。

## :rocket: 使い方 (How to Use)

1.  左上の **"Browse files"** ボタンをクリックして、1つまたは複数のPDFファイルをアップロードします。
2.  処理が自動で開始されます。ファイルごとにプログレスバーが表示されます。
3.  処理が完了すると、抽出結果が表示されます。
4.  **"テキストをダウンロード"** ボタンから、結果をテキストファイルとして保存できます。
5.  サイドバーの「設定」から、OCRの言語や精度などを調整して再実行することも可能です。

## :computer: ローカル環境での動かし方 (Setup for Local Development)

このアプリを自分のPCで動かす場合は、以下の手順に従ってください。

### 1. 前提条件

- [Python](https://www.python.org/) (3.8以上)
- [Tesseract OCRエンジン](https://github.com/tesseract-ocr/tesseract)
    - **Windows:** [UB-Mannheimのインストーラー](https://github.com/UB-Mannheim/tesseract/wiki) を使うのが簡単です。インストール時に「Japanese」と「English」の言語パックも選択してください。
    - **macOS:** `brew install tesseract tesseract-lang`
    - **Linux (Debian/Ubuntu):** `sudo apt-get install tesseract-ocr tesseract-ocr-jpn tesseract-ocr-eng`

### 2. リポジトリをクローン

```bash
git clone https://github.com/あなたのユーザー名/あなたのリポジトリ名.git
cd あなたのリポジトリ名
```

### 3. 必要なライブラリをインストール

仮想環境を作成し、`requirements.txt` を使してライブラリをインストールすることを推奨します。

```bash
# 仮想環境を作成
python -m venv .venv

# 仮想環境を有効化
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# ライブラリをインストール
pip install -r requirements.txt
```

### 4. アプリを実行

```bash
streamlit run app.py
```

ブラウザで `http://localhost:8501` が自動的に開きます。

## :gear: 技術スタック (Technology Stack)

- **Application Framework:** [Streamlit](https://streamlit.io/)
- **PDF Processing:** [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/)
- **OCR Engine:** [Tesseract](https://github.com/tesseract-ocr/tesseract)
- **OCR Wrapper:** [pytesseract](https://pypi.org/project/pytesseract/)
- **Image Processing:** [Pillow](https://python-pillow.org/)

## :memo: ライセンス (License)

このプロジェクトは [MIT License](LICENSE) のもとで公開されています。
