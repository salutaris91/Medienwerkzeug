import os

import pytest

from gui.core.nfo_mutation import (
    NfoConflictError,
    assert_nfo_fingerprint,
    make_nfo_fingerprint,
    patch_nfo_fields,
)


def test_fsk_patch_preserves_every_unrelated_byte(tmp_path):
    nfo_path = tmp_path / "movie.nfo"
    original = (
        b'\xef\xbb\xbf<?xml version="1.0" encoding="UTF-8"?>\n'
        b'<!-- behalten -->\n<movie>\n  <title>M\xc3\xa4nner &amp; B\xc3\xa4ume</title>\n'
        b'  <custom foo="bar">Wert</custom>\n</movie>\n<!-- danach -->'
    )
    nfo_path.write_bytes(original)

    ok, message = patch_nfo_fields(str(nfo_path), {"fsk": "12"})

    assert ok, message
    expected = original.replace(b"</movie>", b"  <mpaa>FSK 12</mpaa>\n</movie>")
    assert nfo_path.read_bytes() == expected


def test_patch_changes_only_selected_fields_and_preserves_existing_values(tmp_path):
    nfo_path = tmp_path / "tvshow.nfo"
    nfo_path.write_text(
        "<tvshow>\n  <title>Alt</title>\n  <plot>Bestehend</plot>\n"
        "  <year>2020</year>\n  <mpaa>FSK 6</mpaa>\n</tvshow>\n",
        encoding="utf-8",
    )

    ok, message = patch_nfo_fields(str(nfo_path), {"plot": "Neu", "fsk": ""})

    assert ok, message
    content = nfo_path.read_text(encoding="utf-8")
    assert "<title>Alt</title>" in content
    assert "<plot>Neu</plot>" in content
    assert "<year>2020</year>" in content
    assert "<mpaa>FSK 6</mpaa>" in content


def test_patch_updates_genres_without_touching_other_metadata(tmp_path):
    nfo_path = tmp_path / "movie.nfo"
    nfo_path.write_text(
        "<movie>\n  <title>Film</title>\n  <genre>Drama</genre>\n"
        "  <genre>Alt</genre>\n  <studio>Studio</studio>\n</movie>\n",
        encoding="utf-8",
    )

    ok, message = patch_nfo_fields(str(nfo_path), {"genres": ["Drama", "Komödie"]})

    assert ok, message
    content = nfo_path.read_text(encoding="utf-8")
    assert content.count("<genre>") == 2
    assert "<genre>Komödie</genre>" in content
    assert "<studio>Studio</studio>" in content


def test_patch_preserves_declared_single_byte_encoding(tmp_path):
    nfo_path = tmp_path / "movie.nfo"
    original = (
        '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        '<movie>\n  <title>Alt</title>\n  <plot>Gr\xfc\xdfe</plot>\n</movie>\n'
    ).encode("latin-1")
    nfo_path.write_bytes(original)

    ok, message = patch_nfo_fields(str(nfo_path), {"title": "K\xf6nig"})

    assert ok, message
    updated = nfo_path.read_bytes()
    assert b'encoding="ISO-8859-1"' in updated
    assert b"<title>K\xf6nig</title>" in updated
    assert b"<plot>Gr\xfc\xdfe</plot>" in updated


def test_fingerprint_detects_modified_and_new_files(tmp_path):
    nfo_path = tmp_path / "tvshow.nfo"
    nfo_path.write_text("<tvshow><title>A</title></tvshow>", encoding="utf-8")
    fingerprint = make_nfo_fingerprint(str(nfo_path))

    nfo_path.write_text("<tvshow><title>B</title></tvshow>", encoding="utf-8")
    with pytest.raises(NfoConflictError):
        assert_nfo_fingerprint(str(nfo_path), fingerprint)

    missing_path = tmp_path / "missing.nfo"
    assert_nfo_fingerprint(str(missing_path), None)
    missing_path.write_text("<movie></movie>", encoding="utf-8")
    with pytest.raises(NfoConflictError):
        assert_nfo_fingerprint(str(missing_path), None)
