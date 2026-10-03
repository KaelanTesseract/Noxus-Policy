# Copyright (c) 2026 Dennis Guse. All rights reserved.
# Licensed under the MIT License. See LICENSE file in project root.

"""Which pages of a long PDF are read, and how a text layer is read."""

import pytest

import ocr
import page_select as ps
import llm_text


def _pdf(pages):
    """A small valid PDF (Helvetica text, one line per page) built by hand."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(len(pages)))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>")
    for i, text in enumerate(pages):
        page_no, content_no = 3 + 2 * i, 4 + 2 * i
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {content_no} 0 R "
                       f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>")
        stream = f"BT /F1 12 Tf 50 780 Td ({text}) Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{n} 0 obj\n{body}\nendobj\n".encode("latin-1")
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)


# ----- page choice for a text layer ----------------------------------------------------------

def _pages(count, rich_at=()):
    return [("Versicherungsschein-Nr. AB-1234567-001 Beitrag 55,00 € Beginn 01.01.2020" if i in rich_at else "Allgemeiner Text ohne Zahlen")
            for i in range(count)]


def test_a_short_document_is_kept_whole():
    assert ps.choose_text_pages(_pages(8)) == list(range(8))


def test_a_premium_table_in_the_middle_of_a_long_document_is_kept():
    chosen = ps.choose_text_pages(_pages(20, rich_at={9, 10}))
    assert 9 in chosen and 10 in chosen            # the old rule (first 5, last 3) lost them
    assert chosen[:3] == [0, 1, 2]                 # letterhead pages always
    assert len(chosen) == ps.MAX_TEXT_PAGES and chosen == sorted(chosen)


def test_without_data_the_first_pages_win_ties():
    assert ps.choose_text_pages(_pages(20)) == list(range(ps.MAX_TEXT_PAGES))


@pytest.mark.parametrize("text,expected", [
    ("Gesamtbeitrag inkl. 19 % Versicherungssteuer (9,98 €) 62,48 €", True),
    ("Jahresbeitrag Gültig ab 24.07.2026\n29,29 €", True),
    ("Wir danken Ihnen für Ihr Vertrauen", False),
    ("Selbstbeteiligung 150 €", False),
    ("", False),
])
def test_has_premium(text, expected):
    assert ps.has_premium(text) is expected


def test_split_pdftotext_drops_the_trailing_empty_page():
    assert ps.split_pdftotext("a\fb\f") == ["a", "b"]
    assert ps.split_pdftotext("") == []


# ----- reading the text layer ---------------------------------------------------------------

@pytest.mark.parametrize("with_pdftotext", [True, False])
def test_a_text_layer_is_read_with_and_without_pdftotext(tmp_path, monkeypatch, with_pdftotext):
    path = tmp_path / "brief.pdf"
    path.write_bytes(_pdf(["Seite eins Beitrag 12,34 EUR", "Seite zwei"]))
    if not with_pdftotext:
        monkeypatch.setattr(ocr.shutil, "which", lambda name: None)
    layer = ocr.read_text_layer(str(path))
    assert len(layer) == 2
    assert "Beitrag 12,34 EUR" in layer[0] and "Seite zwei" in layer[1]


def test_the_text_layer_falls_back_to_pypdf_when_pdftotext_fails(tmp_path, monkeypatch):
    path = tmp_path / "brief.pdf"
    path.write_bytes(_pdf(["Hallo Welt"]))
    monkeypatch.setattr(ocr.shutil, "which", lambda name: "pdftotext")
    def boom(*a, **k):
        raise OSError("kaputt")
    monkeypatch.setattr(ocr.subprocess, "run", boom)
    assert "Hallo Welt" in ocr.read_text_layer(str(path))[0]


def test_extract_text_keeps_page_markers_and_picks_pages_of_a_long_pdf(tmp_path):
    texts = [f"Seite {i + 1} Text" for i in range(14)]
    texts[10] = "Versicherungsschein-Nr. AB-1234567-001 Beitrag 55,00 EUR Beginn 01.01.2020"
    path = tmp_path / "lang.pdf"
    path.write_bytes(_pdf(texts))
    result = ocr.extract_text_from_file(str(path))
    assert "--- Page 1 ---" in result and "--- Page 11 ---" in result
    assert "Beitrag 55,00 EUR" in result
    assert "--- Page 14 ---" not in result


# ----- scanned PDFs: more pages only when needed -----------------------------------------------

class _Pages:
    """Stands in for pdf2image and Tesseract: page n 'reads' as texts[n-1]."""

    def __init__(self, monkeypatch, texts):
        self.texts, self.rendered = texts, []
        monkeypatch.setattr(ocr, "_pdf_page_count", lambda path: len(texts))
        monkeypatch.setattr(ocr, "convert_from_path", self.convert)
        monkeypatch.setattr(ocr, "read_page_image", lambda img: self.texts[img - 1])

    def convert(self, path, first_page, last_page, **kw):
        last = min(last_page, len(self.texts))
        self.rendered.append((first_page, last))
        return list(range(first_page, last + 1))


def test_a_scan_is_read_in_batches_until_a_premium_is_found(monkeypatch):
    texts = ["Brief ohne Zahlen"] * 12
    texts[8] = "Gesamtbeitrag 62,48 €"
    stub = _Pages(monkeypatch, texts)
    result = ocr.ocr_pdf_pages("scan.pdf")
    assert stub.rendered == [(1, 5), (6, 8), (9, 11)]      # stops after the batch with page 9
    assert "Gesamtbeitrag 62,48 €" in result and "--- Page 9 ---" in result


def test_a_scan_with_the_premium_on_the_first_pages_is_read_only_once(monkeypatch):
    texts = ["Beitrag 12,00 €"] + ["x"] * 20
    stub = _Pages(monkeypatch, texts)
    ocr.ocr_pdf_pages("scan.pdf")
    assert stub.rendered == [(1, 5)]


def test_an_information_leaflet_is_not_read_to_the_end(monkeypatch):
    texts = ["Verbraucherinformationen", "für Kraftfahrtversicherungen"] + ["Text"] * 60
    stub = _Pages(monkeypatch, texts)
    ocr.ocr_pdf_pages("scan.pdf")
    assert stub.rendered == [(1, 5)]


def test_a_scan_without_any_premium_stops_at_the_limit(monkeypatch):
    stub = _Pages(monkeypatch, ["Text"] * 40)
    ocr.ocr_pdf_pages("scan.pdf")
    assert stub.rendered[-1][1] == ps.MAX_OCR_PAGES


def test_a_short_scan_is_not_asked_for_more_pages_than_it_has(monkeypatch):
    stub = _Pages(monkeypatch, ["Text", "Text"])
    ocr.ocr_pdf_pages("scan.pdf")
    assert stub.rendered == [(1, 2)]


def test_wide_gaps_of_a_layout_text_do_not_cut_off_the_right_column():
    line = "Jahresbeitrag" + " " * 150 + "29,29 €"
    picked = llm_text.select_relevant_text(line + "\n" + "x\n" * 3000, 500)
    assert "29,29 €" in picked
