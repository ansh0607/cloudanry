from backend.services.search import keyword_search


def test_matches_tag_with_higher_weight_than_description():
    items = [
        {"id": "desc_only", "ai_tags": [], "image_description": "trees planted"},
        {"id": "tag", "ai_tags": ["trees"], "image_description": "something else"},
    ]
    results = keyword_search(items, "trees")
    assert results[0]["id"] == "tag"


def test_case_insensitive_and_substring():
    items = [{"id": "m", "ai_tags": ["Reforestation"], "image_description": ""}]
    assert keyword_search(items, "forest")[0]["id"] == "m"


def test_no_match_returns_empty():
    items = [{"id": "m", "ai_tags": ["river"], "image_description": "a river"}]
    assert keyword_search(items, "volcano") == []


def test_empty_query_returns_empty():
    assert keyword_search([{"id": "m", "ai_tags": ["x"]}], "") == []


def test_cloudinary_tags_also_searched():
    items = [{"id": "m", "ai_tags": [], "cloudinary_tags": ["solar"], "image_description": ""}]
    assert keyword_search(items, "solar")[0]["id"] == "m"
