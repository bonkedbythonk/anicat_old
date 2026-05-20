from anicat_media.libs.media_api.jikan import mapper


def make_item(mal_id: int, english: str, romaji: str = "") -> dict:
    titles = []
    if english:
        titles.append({"type": "English", "title": english})
    if romaji:
        titles.append({"type": "Default", "title": romaji})
    return {"mal_id": mal_id, "titles": titles, "images": {"jpg": {}}, "status": "Currently Airing"}


def test_fuzzy_promotes_strong_match():
    # Two items where item 2 is the intended match for the noisy query
    item1 = make_item(101, "Some Other Show", "Some Other Show")
    item2 = make_item(202, "Fullmetal Alchemist: Brotherhood", "Hagane no Renkinjutsushi")

    api_response = {"data": [item1, item2], "pagination": {"items": {"total": 2, "per_page": 25}, "current_page": 1, "has_next_page": False}}

    noisy_query = "Hey, what was that fullmetal alchemist brotherhood 2009 blu-ray release called again?"

    result = mapper.to_generic_search_result(api_response, original_query=noisy_query)
    assert result is not None
    # Expect the Fullmetal item to be promoted to the first position
    assert result.media[0].title.english and "Fullmetal" in result.media[0].title.english
