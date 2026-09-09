# app/core/nltk_setup.py
"""
Makes sure the NLTK language data our features depend on is present.

Sentence splitting (used when rendering pages and searching inside a book)
and the WordNet lookups (used by the vocabulary/dictionary feature) both
need small data packages that NLTK does not ship by default. Without them,
the first page a user opens raises a confusing LookupError instead of
just working, so we fetch anything missing once at startup.
"""
import nltk

REQUIRED_PACKAGES = [
    ("tokenizers/punkt_tab", "punkt_tab"),
    ("corpora/wordnet", "wordnet"),
    ("corpora/omw-1.4", "omw-1.4"),
]


def ensure_nltk_data() -> None:
    for lookup_path, package_name in REQUIRED_PACKAGES:
        try:
            nltk.data.find(lookup_path)
        except LookupError:
            nltk.download(package_name, quiet=True)
