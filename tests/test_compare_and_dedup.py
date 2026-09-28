import io

import numpy as np
from PIL import Image

from backend.services.compare import compare_media, green_pixel_ratio, pixel_diff_percent
from backend.services.dedup import similarity_percent


def _img_bytes(color, size=(200, 200)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _greenish(tone=80) -> bytes:
    return _img_bytes((30, tone, 40))


def _bare(tone=120) -> bytes:
    return _img_bytes((tone, 30, 30))


def test_green_ratio_high_for_green_image():
    assert green_pixel_ratio(_greenish()) > 0.9


def test_green_ratio_low_for_bare_image():
    assert green_pixel_ratio(_bare()) < 0.1


def test_pixel_diff_zero_for_identical():
    data = _greenish()
    assert pixel_diff_percent(data, data) < 1.0


def test_pixel_diff_high_for_different():
    assert pixel_diff_percent(_greenish(), _bare()) > 10.0


def test_compare_media_payload_shape():
    a, b = _bare(), _greenish()
    media_a = {"id": "A", "capture_date": "2026-01-01"}
    media_b = {"id": "B", "capture_date": "2026-02-01"}
    result = compare_media(media_a, media_b, a, b)
    assert result["media_a_id"] == "A" and result["media_b_id"] == "B"
    assert result["chronological_order"] is True
    assert result["green_ratio_b"] > result["green_ratio_a"]
    assert 0 <= result["pixel_diff_percent"] <= 100


def test_identical_images_are_perfect_duplicates():
    h1 = str(__import__("imagehash").phash(Image.open(io.BytesIO(_greenish()))))
    h2 = str(__import__("imagehash").phash(Image.open(io.BytesIO(_greenish()))))
    assert similarity_percent(h1, h2) == 100.0


def test_different_images_score_below_threshold():
    h1 = str(__import__("imagehash").phash(Image.open(io.BytesIO(_greenish()))))
    noise = np.random.randint(0, 255, (200, 200, 3), dtype=np.uint8)
    buf = io.BytesIO()
    Image.fromarray(noise).save(buf, format="JPEG")
    h2 = str(__import__("imagehash").phash(Image.open(io.BytesIO(buf.getvalue()))))
    assert similarity_percent(h1, h2) < 90.0
