# app/core/constants.py

# Server Configurations
HOST = "127.0.0.1"
PORT = 5000
RELOAD = True

# Allowed file formats
ALLOWED_EXTENSIONS = ["pdf", "epub"]

# Online dictionary API for additional word details
DICTIONARY_API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"

# Morphological analysis configuration
PREFIXES = {
    "un": {"meaning": "not, opposite of", "role": "prefix of negation"},
    "re": {"meaning": "again, back", "role": "prefix of repetition/reversion"},
    "dis": {"meaning": "not, opposite of, reverse", "role": "prefix of negation/reversal"},
    "mis": {"meaning": "wrongly, badly", "role": "prefix of error/evaluation"},
    "pre": {"meaning": "before, in advance", "role": "prefix of time/space"},
    "post": {"meaning": "after, behind", "role": "prefix of time/space"},
    "in": {"meaning": "not / in, into", "role": "prefix of negation/direction"},
    "im": {"meaning": "not / in, into", "role": "prefix of negation/direction (used before b, m, p)"},
    "il": {"meaning": "not", "role": "prefix of negation (used before l)"},
    "ir": {"meaning": "not", "role": "prefix of negation (used before r)"},
    "de": {"meaning": "down, off, away, reverse", "role": "prefix of reversal/reduction"},
    "sub": {"meaning": "under, below", "role": "prefix of lower position/degree"},
    "super": {"meaning": "above, over, exceeding", "role": "prefix of superiority/excess"},
    "trans": {"meaning": "across, beyond, through", "role": "prefix of movement/change"},
    "pro": {"meaning": "forward, in favor of", "role": "prefix of support/direction"},
    "anti": {"meaning": "against, opposing", "role": "prefix of opposition"},
    "co": {"meaning": "together, with", "role": "prefix of association/collaboration"},
    "non": {"meaning": "not", "role": "prefix of simple negation"}
}

SUFFIXES = {
    "able": {"meaning": "capable of, fit for", "role": "adjective-forming suffix"},
    "ible": {"meaning": "capable of, fit for", "role": "adjective-forming suffix"},
    "al": {"meaning": "relating to / action of", "role": "adjective or noun-forming suffix"},
    "er": {"meaning": "one who, that which", "role": "noun-forming agent suffix"},
    "or": {"meaning": "one who, that which", "role": "noun-forming agent suffix"},
    "ful": {"meaning": "full of, characterized by", "role": "adjective-forming suffix"},
    "less": {"meaning": "without, lacking", "role": "adjective-forming suffix"},
    "ly": {"meaning": "in the manner of", "role": "adverb-forming suffix"},
    "ment": {"meaning": "action, state, process", "role": "noun-forming suffix"},
    "ness": {"meaning": "state, quality, condition", "role": "noun-forming abstract suffix"},
    "tion": {"meaning": "state, condition, action", "role": "noun-forming action suffix"},
    "sion": {"meaning": "state, condition, action", "role": "noun-forming action suffix"},
    "ity": {"meaning": "state, quality, condition", "role": "noun-forming property suffix"},
    "ty": {"meaning": "state, quality, condition", "role": "noun-forming property suffix"},
    "ous": {"meaning": "full of, possessing", "role": "adjective-forming suffix"},
    "ive": {"meaning": "tending to, having the quality of", "role": "adjective-forming suffix"},
    "ic": {"meaning": "relating to, like", "role": "adjective-forming suffix"},
    "ish": {"meaning": "somewhat like, having the origin", "role": "adjective-forming suffix"},
    "y": {"meaning": "characterized by, full of", "role": "adjective or noun-forming suffix"},
    "est": {"meaning": "most (superlative)", "role": "superlative adjective/adverb inflection"},
    "ed": {"meaning": "past action or state", "role": "verb past tense or past participle inflection"},
    "ing": {"meaning": "action, process / present participle", "role": "verb continuous inflection / noun / adjective"}
}

ROOTS = {
    "dict": {"meaning": "say, speak", "origin": "Latin 'dictus'"},
    "spect": {"meaning": "look, see", "origin": "Latin 'spectare'"},
    "port": {"meaning": "carry", "origin": "Latin 'portare'"},
    "aud": {"meaning": "hear", "origin": "Latin 'audire'"},
    "scrib": {"meaning": "write", "origin": "Latin 'scribere'"},
    "script": {"meaning": "write", "origin": "Latin 'scriptus'"},
    "vis": {"meaning": "see", "origin": "Latin 'visus'"},
    "vid": {"meaning": "see", "origin": "Latin 'videre'"},
    "cred": {"meaning": "believe", "origin": "Latin 'credere'"},
    "struct": {"meaning": "build, construct", "origin": "Latin 'structus'"},
    "auto": {"meaning": "self", "origin": "Greek 'autos'"},
    "bio": {"meaning": "life", "origin": "Greek 'bios'"},
    "chron": {"meaning": "time", "origin": "Greek 'chronos'"},
    "graph": {"meaning": "write, draw", "origin": "Greek 'graphein'"},
    "phon": {"meaning": "sound", "origin": "Greek 'phone'"},
    "tele": {"meaning": "far, distant", "origin": "Greek 'tele'"},
    "path": {"meaning": "feeling, suffering", "origin": "Greek 'pathos'"},
    "phil": {"meaning": "love", "origin": "Greek 'philein'"},
    "tract": {"meaning": "drag, pull", "origin": "Latin 'tractus'"},
    "inject": {"meaning": "throw, introduce", "origin": "Latin 'jacere'"},
    "rupt": {"meaning": "break, burst", "origin": "Latin 'ruptus'"},
    "bene": {"meaning": "good, well", "origin": "Latin 'bene'"},
    "mal": {"meaning": "bad, evil", "origin": "Latin 'malus'"},
    "fact": {"meaning": "do, make", "origin": "Latin 'factus'"}
}
