import io
import re
from typing import List, Tuple, Optional
import streamlit as st
from PIL import Image
import fitz  # PyMuPDF
import pytesseract
st.set_page_config(page_title="PDF → Text (with OCR) + 章抽出 + 整形", page_icon=":page_facing_up:", layout="wide")
st.title(":page_facing_up: PDF → Text (with OCR) ／ 章抽出（原文保持）＋ 整形オプション")
# ========= サイドバー（抽出設定） =========
with st.sidebar:
    st.header("抽出エンジン設定")
    ocr_lang = st.text_input("OCR言語（Tesseractコード）", value="jpn+eng")
    dpi = st.slider("OCR用レンダリングDPI", 150, 600, 300, 50)
    min_chars = st.slider("OCR切替の閾値（抽出テキストの最小文字数）", 0, 200, 10, 5)
    keep_layout = st.checkbox("段組をなるべく保持して抽出（blocks→lines）", value=False)
    show_per_page = st.checkbox("ページごとの表示", value=True)
    show_debug = st.checkbox("デバッグ情報を表示", value=False)
st.markdown("---")
# ========= 範囲指定（原文スライス） =========
st.subheader(":mag_right: 範囲抽出（“一言一句”そのまま）")
with st.expander("抽出条件（開始/終了）を指定", expanded=True):
    st.caption("※ 既定は『第2章』の見出し行～『第3章』直前まで。見出し表記の揺れは正規表現を調整してください。")
    use_regex = st.checkbox("正規表現として解釈する", value=True)
    default_start = r"^\s*第\s*2\s*章.*$"
    default_end   = r"^\s*第\s*3\s*章\b"
    start_query = st.text_input("開始（見出し）", value=default_start)
    end_query = st.text_input("終了（次の見出し。空なら文末まで）", value=default_end)
# ========= 整形オプション =========
st.subheader(":soap: 文章整形（原文は保持しつつ“見やすい版”を生成）")
with st.expander("整形オプション", expanded=False):
    enable_fix = st.checkbox("整形処理を有効化（原文は別枠で保持）", value=True)
    fix_line_wrap = st.checkbox("段落内の変な改行を結合（日本語向け）", value=True, disabled=not enable_fix)
    fix_hyphen = st.checkbox("行末ハイフンで分割された英単語を結合", value=True, disabled=not enable_fix)
    collapse_blank = st.checkbox("連続する空行を1行に圧縮", value=True, disabled=not enable_fix)
    latin_space_norm = st.checkbox("英数字の余分なスペースを1つに（日本語はそのまま）", value=True, disabled=not enable_fix)
    trim_each_line = st.checkbox("各行の前後空白をトリム", value=False, disabled=not enable_fix)
    remove_soft_hyphen = st.checkbox("ソフトハイフン(\\u00AD)を除去", value=True, disabled=not enable_fix)
uploaded_files = st.file_uploader("PDFファイルをアップロード（複数可）", accept_multiple_files=True, type=["pdf"])
# ========= テキスト抽出ロジック =========
def extract_page_text(page: fitz.Page, keep_layout: bool = False) -> str:
    """PyMuPDFの生テキスト抽出。keep_layout=Trueならblocks→linesで簡易に段組崩れを抑える。"""
    if not keep_layout:
        return page.get_text("text") or ""
    blocks = page.get_text("blocks") or []
    blocks_sorted = sorted(blocks, key=lambda b: (round(b[1], 1), round(b[0], 1)))
    lines: List[str] = []
    for b in blocks_sorted:
        text = (b[4] or "").rstrip("\n")
        if text:
            lines.append(text)
    return "\n\n".join(lines)
def page_text_or_ocr(page: fitz.Page, ocr_lang: str, dpi: int, min_chars: int, keep_layout: bool) -> Tuple[str, dict]:
    """1) 生抽出 2) しきい値未満ならOCRへフォールバック。"""
    meta = {"method": "text", "chars": 0, "ocr_dpi": None}
    text = extract_page_text(page, keep_layout=keep_layout) or ""
    if len(text.strip()) >= min_chars:
        meta["chars"] = len(text.strip())
        return text, meta
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    ocr_text = pytesseract.image_to_string(img, lang=ocr_lang) or ""
    meta.update({"method": "ocr", "chars": len(ocr_text.strip()), "ocr_dpi": dpi})
    return ocr_text, meta
def process_pdf(file_bytes: bytes, keep_layout: bool, ocr_lang: str, dpi: int, min_chars: int):
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    all_pages_text: List[str] = []
    per_page_info: List[dict] = []
    progress_bar = st.progress(0.0, text="処理中…")
    for i, page in enumerate(doc, start=1):
        txt, meta = page_text_or_ocr(page, ocr_lang=ocr_lang, dpi=dpi, min_chars=min_chars, keep_layout=keep_layout)
        all_pages_text.append(txt)
        meta["page"] = i
        per_page_info.append(meta)
        progress_bar.progress(i / len(doc), text=f"{i}/{len(doc)} ページ")
    progress_bar.empty()
    return all_pages_text, per_page_info
# ========= 範囲検出（原文スライス専用） =========
def find_span(text: str, start_q: str, end_q: Optional[str], regex: bool) -> Tuple[Optional[int], Optional[int], Optional[str]]:
    """textから開始～終了のインデックスを返す（終了は直前まで）。見つからない場合は理由付きでNone。"""
    if regex:
        start_m = re.search(start_q, text, flags=re.MULTILINE)
        if not start_m:
            return None, None, "開始見出しが見つかりませんでした。パターンを調整してください。"
        start_idx = start_m.start()
        if end_q:
            end_m = re.search(end_q, text, flags=re.MULTILINE)
            if not end_m:
                return start_idx, len(text), "終了見出しが見つからないため、文末まで抽出しました。"
            end_idx = end_m.start()
        else:
            end_idx = len(text)
        return start_idx, end_idx, None
    else:
        sidx = text.find(start_q)
        if sidx == -1:
            return None, None, "開始キーワードが見つかりませんでした。"
        if end_q:
            eidx = text.find(end_q, sidx + len(start_q))
            if eidx == -1:
                return sidx, len(text), "終了キーワードが見つからないため、文末まで抽出しました。"
            return sidx, eidx, None
        return sidx, len(text), None
# ========= 整形処理（“見やすい版”） =========
def fix_text_readability(text: str,
                         fix_line_wrap: bool = True,
                         fix_hyphen: bool = True,
                         collapse_blank: bool = True,
                         latin_space_norm: bool = True,
                         trim_each_line: bool = False,
                         remove_soft_hyphen: bool = True) -> str:
    """
    読みやすさ向上のための非破壊的（意味を変えない範囲の）整形。
    ※ 原文保持は別で行うため、ここでは見やすさ重視の変更を行う。
    """
    t = text
    # ソフトハイフン（SHY）の除去（OCR/コピー由来）
    if remove_soft_hyphen:
        t = t.replace("\u00AD", "")
    # 行末ハイフネーション解除: "inter-\nnational" → "international"
    if fix_hyphen:
        # 英単語っぽい分割のみ対象（日本語の「ー」は触らない）
        t = re.sub(r"([A-Za-z])-\n([A-Za-z])", r"\1\2", t)
    # 段落内の変な改行を結合（日本語向け）
    if fix_line_wrap:
        # 1) 「句点や閉じカッコで終わらない行」の改行は結合（和文は基本的に行内スペース不要）
        # 対象終端: 。，、」』】）」!?…）〉》〕］
        not_end_punct = r"[^。．！!？\?、，…」』】）」〉》〕］＞>）)\]]"
        # 改行の直後が行頭記号や箇条書き等でなければ連結
        # 次行先頭が「・○●-」等で始まる場合は段落とみなして残す
        pattern = re.compile(rf"({not_end_punct})\n(?!\s*[・\-—―○●◇◆:arrow_forward:▷■□①-⑳\*\u2022])")
        # 日本語は基本スペース不要。前後が英数字の場合のみスペースを挿入。
        def _join(m):
            left = m.group(1)
            return left + (" " if re.search(r"[A-Za-z0-9]$", left) else "")
        t = pattern.sub(lambda m: _join(m), t)
        # 2) 行中の「数字/英字 と 英字/数字」の改行はスペースで結合（例: "Fig.\n1" → "Fig. 1"）
        t = re.sub(r"([A-Za-z0-9])\n(?=[A-Za-z0-9])", r"\1 ", t)
    # 連続空行の圧縮
    if collapse_blank:
        t = re.sub(r"\n{3,}", "\n\n", t)
    # 英数字の余分なスペースを1つに（和文の全角は触らない）
    if latin_space_norm:
        # 連続半角スペースを1つに
        t = re.sub(r"[ ]{2,}", " ", t)
    # 各行の前後空白トリム（日本語の先頭全角スペースは残したい場合はFalse推奨）
    if trim_each_line:
        t = "\n".join([ln.strip() for ln in t.splitlines()])
    return t
# ========= メインUI =========
if uploaded_files:
    for up in uploaded_files:
        st.subheader(f":blue_book: {up.name}")
        file_bytes = up.read()
        with st.spinner("抽出中…"):
            pages_text, info = process_pdf(file_bytes, keep_layout, ocr_lang, dpi, min_chars)
        # 原文（ページ連結）— ここからだけ切り出す！
        joined_text = "\n\n".join(pages_text)
        # 範囲抽出（原文そのまま）
        st.markdown("### :scissors: 範囲抽出（原文そのまま）")
        sidx, eidx, warn = find_span(joined_text, start_query, end_query.strip() or None, use_regex)
        if sidx is not None and eidx is not None:
            slice_text_raw = joined_text[sidx:eidx]  # 原文スライス
            if warn:
                st.info(warn)
            st.markdown("**抽出結果（原文そのまま）**")
            st.code(slice_text_raw or "", language="text")
            st.download_button(
                "抽出テキスト（原文そのまま）をダウンロード",
                data=slice_text_raw.encode("utf-8"),
                file_name=up.name.rsplit(".", 1)[0] + "_section_raw.txt",
                mime="text/plain",
                use_container_width=True,
            )
            # 整形版の生成・表示・DL
            if enable_fix:
                slice_text_fixed = fix_text_readability(
                    slice_text_raw,
                    fix_line_wrap=fix_line_wrap,
                    fix_hyphen=fix_hyphen,
                    collapse_blank=collapse_blank,
                    latin_space_norm=latin_space_norm,
                    trim_each_line=trim_each_line,
                    remove_soft_hyphen=remove_soft_hyphen,
                )
                st.markdown("**抽出結果（整形版）**")
                st.code(slice_text_fixed or "", language="text")
                st.download_button(
                    "抽出テキスト（整形版）をダウンロード",
                    data=slice_text_fixed.encode("utf-8"),
                    file_name=up.name.rsplit(".", 1)[0] + "_section_fixed.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
        else:
            st.warning(warn or "抽出範囲を見つけられませんでした。開始/終了の指定を見直してください。")
        st.markdown("---")
        # :outbox_tray: 全文ダウンロード（原文 / 整形）
        st.markdown("### :outbox_tray: 全文エクスポート")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "全文（原文そのまま）.txt をダウンロード",
                data=joined_text.encode("utf-8"),
                file_name=up.name.rsplit(".", 1)[0] + ".txt",
                mime="text/plain",
                use_container_width=True,
            )
        with col2:
            if enable_fix:
                full_fixed = fix_text_readability(
                    joined_text,
                    fix_line_wrap=fix_line_wrap,
                    fix_hyphen=fix_hyphen,
                    collapse_blank=collapse_blank,
                    latin_space_norm=latin_space_norm,
                    trim_each_line=trim_each_line,
                    remove_soft_hyphen=remove_soft_hyphen,
                )
                st.download_button(
                    "全文（整形版）.txt をダウンロード",
                    data=full_fixed.encode("utf-8"),
                    file_name=up.name.rsplit(".", 1)[0] + "_fixed.txt",
                    mime="text/plain",
                    use_container_width=True,
                )
        # :compass: ページごとの表示
        if show_per_page:
            with st.expander("ページごとのテキスト", expanded=False):
                for idx, t in enumerate(pages_text, start=1):
                    st.markdown(f"**Page {idx}**")
                    st.code(t or "", language="text")
        # :mag_right: 全文プレビュー（原文）
        st.markdown("**全文プレビュー（原文）**")
        st.code(joined_text or "", language="text")
        # :hammer_and_wrench: デバッグ情報
        if show_debug:
            st.markdown("**処理メタ情報**")
            st.table(info)
else:
    st.info("左上の「Browse files」からPDFをアップロードしてください。")
    st.caption("埋め込みテキストは生抽出、スキャンは自動OCRに切り替えます。章抽出は原文からのスライス後、任意で整形を適用します。")





