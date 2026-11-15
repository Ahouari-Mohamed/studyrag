import re, unicodedata

def norm(s):
    """Lowercase, strip accents, unify apostrophes: for tolerant matching."""
    s = (s or "").replace("\u2019", "'").replace("\u2018", "'").replace("\u0131", "i").replace("\u0153", "oe")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()

def norm_name(filename):
    """'2 - Regression Linéaire.pdf' and '2_Regression_Lineaire.pdf' compare equal."""
    base = re.sub(r"\.[A-Za-z0-9]+$", "", filename or "")
    return re.sub(r"[^a-z0-9]", "", norm(base))

def page_ok(found_page, q, tol=1):
    """True if found_page matches the expected page (+- tol) or one of alt_pages."""
    exp = q.get("expected_page")
    if exp is None or found_page is None:
        return True
    if abs(found_page - exp) <= tol:
        return True
    return any(abs(found_page - a) <= tol for a in q.get("alt_pages", []))

def is_match(chunk_file, chunk_page, q, tol=1):
    return norm_name(chunk_file) == norm_name(q["expected_file"]) and page_ok(chunk_page, q, tol)
