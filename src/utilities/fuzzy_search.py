def _fuzzy_score(query: str, text: str) -> int:
    query = query.lower()
    text = text.lower()
    if query in text:
        return 100
    score = 0
    qi = 0
    for ch in text:
        if qi < len(query) and ch == query[qi]:
            score += 1
            qi += 1
    return score if qi == len(query) else 0
