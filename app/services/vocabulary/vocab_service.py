# app/services/vocabulary/vocab_service.py
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from nltk.corpus import wordnet
import ety
import httpx
from app.core.config import settings
from app.core import constants
from app.schemas.schemas import WordAnalysisResponse, MorphologicalComponent


class VocabularyService:
    def __init__(self):
        self.oxford_dict = {}
        self._load_oxford_data()

    def _load_oxford_data(self):
        """Load Oxford 3000 & 5000 databases into memory."""
        try:
            o3_path = os.path.join(settings.BASE_DIR, "app", "static", "data", "oxford_3000.json")
            o5_path = os.path.join(settings.BASE_DIR, "app", "static", "data", "oxford_5000.json")
            
            # Load Oxford 3000
            if os.path.exists(o3_path):
                with open(o3_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        word = v.get("word", "").lower()
                        if word:
                            self.oxford_dict[word] = v
            
            # Load Oxford 5000 (overwriting or extending)
            if os.path.exists(o5_path):
                with open(o5_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        word = v.get("word", "").lower()
                        if word:
                            # Keep existing or upgrade if CEFR level is different
                            self.oxford_dict[word] = v
        except Exception as e:
            print(f"Error loading offline Oxford dictionary files: {e}")

    def clean_word(self, word: str) -> str:
        """Strip punctuation and symbols from a word."""
        return "".join(c for c in word if c.isalnum() or c in "'-").lower().strip()

    def decompose_word(self, word: str) -> Tuple[Optional[str], str, Optional[str]]:
        """
        Decomposes a word into prefix, base word, and suffix based on rules.
        Example: unbelievable -> un- (prefix), believe (base), -able (suffix)
        """
        w = word.lower().strip()
        detected_prefix = None
        detected_suffix = None
        base_word = w

        # 1. Match prefixes
        for pref in sorted(constants.PREFIXES.keys(), key=len, reverse=True):
            if w.startswith(pref) and len(w) > len(pref) + 2:
                detected_prefix = pref
                base_word = w[len(pref):]
                break

        # 2. Match suffixes on remaining base word
        target_for_suffix = base_word
        for suff in sorted(constants.SUFFIXES.keys(), key=len, reverse=True):
            if target_for_suffix.endswith(suff) and len(target_for_suffix) > len(suff) + 2:
                detected_suffix = suff
                base_word = target_for_suffix[:-len(suff)]
                
                # Check for standard suffix sound adjustments (e.g. spelling mutations)
                if suff in ["able", "ible", "tion", "sion"] and not base_word.endswith(("a", "e", "i", "o", "u")):
                    # e.g., believable -> believ -> restore believe
                    test_word = base_word + "e"
                    if wordnet.synsets(test_word):
                        base_word = test_word
                elif suff == "ily" and base_word.endswith(""):
                    # e.g., happily -> happ -> restore happy
                    test_word = base_word + "y"
                    if wordnet.synsets(test_word):
                        base_word = test_word
                break

        # 3. If no suffix matched on the remainder, check the original word
        if not detected_suffix:
            for suff in sorted(constants.SUFFIXES.keys(), key=len, reverse=True):
                if w.endswith(suff) and len(w) > len(suff) + 2:
                    detected_suffix = suff
                    base_word = w[:-len(suff)]
                    if suff in ["able", "ible", "tion", "sion"] and not base_word.endswith(("a", "e", "i", "o", "u")):
                        test_word = base_word + "e"
                        if wordnet.synsets(test_word):
                            base_word = test_word
                    break

        # If base_word is left empty or invalid, reset
        if not base_word:
            base_word = w

        return detected_prefix, base_word, detected_suffix

    def _fetch_online_details(self, word: str) -> Optional[Dict[str, Any]]:
        """Fetch word details from public Free Dictionary API if online."""
        try:
            url = constants.DICTIONARY_API_URL.format(word=word)
            response = httpx.get(url, timeout=1.5)
            if response.status_code == 200:
                data = response.json()
                if data and isinstance(data, list) and len(data) > 0:
                    return data[0]
        except Exception as e:
            # Silent fallback to offline dataset
            print(f"Skipping online lookup for '{word}' (offline or API timeout): {e}")
        return None

    def analyze_word(self, raw_word: str) -> WordAnalysisResponse:
        """
        Performs a full online/offline semantic, etymological, and morphological analysis on a word.
        """
        word = self.clean_word(raw_word)
        if not word:
            return WordAnalysisResponse(word=raw_word)

        # Initialize collections
        definitions = []
        examples = []
        synonyms_set = set()
        antonyms_set = set()
        pronunciation = None
        ipa = None
        part_of_speech = None
        cefr = None
        frequency = None

        # 0. Try online lookup first for pronunciation audio, detailed IPA and descriptions
        online_data = self._fetch_online_details(word)
        if online_data:
            # Extract IPA phonetic
            ipa = online_data.get("phonetic")
            if not ipa:
                for p in online_data.get("phonetics", []):
                    if p.get("text"):
                        ipa = p.get("text")
                        break
            
            # Extract audio link (UK/US mp3)
            for p in online_data.get("phonetics", []):
                if p.get("audio"):
                    pronunciation = p.get("audio")
                    break

            # Parse online meanings
            for meaning in online_data.get("meanings", []):
                pos = meaning.get("partOfSpeech")
                if pos and not part_of_speech:
                    part_of_speech = pos
                
                # Definitions, examples, synonyms, antonyms
                for d_obj in meaning.get("definitions", []):
                    d_text = d_obj.get("definition")
                    if d_text and d_text not in definitions:
                        definitions.append(d_text)
                    ex = d_obj.get("example")
                    if ex and ex not in examples:
                        examples.append(ex)
                    
                    for s in d_obj.get("synonyms", []):
                        synonyms_set.add(s)
                    for a in d_obj.get("antonyms", []):
                        antonyms_set.add(a)

                for s in meaning.get("synonyms", []):
                    synonyms_set.add(s)
                for a in meaning.get("antonyms", []):
                    antonyms_set.add(a)

        # 1. Fetch info from local Oxford 3000/5000 dictionary cache
        ox_entry = self.oxford_dict.get(word)
        if ox_entry:
            if not pronunciation:
                pronunciation = ox_entry.get("uk", "")
            if not ipa:
                ipa = ox_entry.get("phon_br") or ox_entry.get("phon_n_am")
            if not part_of_speech:
                part_of_speech = ox_entry.get("type")
            
            local_def = ox_entry.get("definition", "")
            if local_def and local_def not in definitions:
                definitions.append(local_def)
                
            if ox_entry.get("example"):
                for ex in ox_entry.get("example", "").split("."):
                    ex_clean = ex.strip()
                    if ex_clean and ex_clean not in examples:
                        examples.append(ex_clean)
                        
            cefr = ox_entry.get("cefr", "").upper()
            cefr_freq_map = {"A1": 0.9, "A2": 0.75, "B1": 0.6, "B2": 0.45, "C1": 0.3, "C2": 0.15}
            frequency = cefr_freq_map.get(cefr, 0.2)

        # 2. Query WordNet (NLTK) for definitions, parts of speech, synonyms, antonyms, examples
        synsets = wordnet.synsets(word)
        pos_map = {"n": "noun", "v": "verb", "a": "adjective", "r": "adverb", "s": "adjective"}

        for syn in synsets:
            wn_def = syn.definition()
            if wn_def not in definitions:
                definitions.append(wn_def)
            
            for ex in syn.examples():
                if ex not in examples:
                    examples.append(ex)
            
            if not part_of_speech:
                part_of_speech = pos_map.get(syn.pos(), syn.pos())

            for lemma in syn.lemmas():
                syn_name = lemma.name().replace("_", " ")
                if syn_name != word:
                    synonyms_set.add(syn_name)
                for ant in lemma.antonyms():
                    ant_name = ant.name().replace("_", " ")
                    antonyms_set.add(ant_name)

        synonyms = list(synonyms_set)[:10]
        antonyms = list(antonyms_set)[:10]

        # 3. Etymology tracing via `ety` library (offline)
        etymology = None
        etymology_tree = None
        try:
            origins = ety.origins(word)
            if origins:
                origins_str = ", ".join([f"{o.word} ({o.language.name})" for o in origins])
                etymology = f"Derived from: {origins_str}."
                tree_str = ety.tree(word)
                if tree_str:
                    etymology_tree = str(tree_str)
        except Exception:
            pass

        # 4. Morphological Prefix, Suffix, Root analysis
        pref, base, suff = self.decompose_word(word)
        
        prefix_analysis = None
        if pref and pref in constants.PREFIXES:
            prefix_analysis = MorphologicalComponent(
                component=f"{pref}-",
                meaning=constants.PREFIXES[pref]["meaning"],
                role=constants.PREFIXES[pref]["role"]
            )
            
        suffix_analysis = None
        if suff and suff in constants.SUFFIXES:
            suffix_analysis = MorphologicalComponent(
                component=f"-{suff}",
                meaning=constants.SUFFIXES[suff]["meaning"],
                role=constants.SUFFIXES[suff]["role"]
            )

        root_analysis = None
        root_match = None
        for r_key, r_val in constants.ROOTS.items():
            if r_key in base:
                root_match = r_key
                root_analysis = MorphologicalComponent(
                    component=r_key,
                    meaning=r_val["meaning"],
                    role=f"Root morpheme ({r_val['origin']})"
                )
                break

        # Estimate CEFR level if not found in Oxford lists based on word length / complexity
        if not cefr:
            if len(synsets) == 0:
                cefr = "C2"
                frequency = 0.05
            else:
                length = len(word)
                if length <= 4:
                    cefr = "A2"
                    frequency = 0.8
                elif length <= 7:
                    cefr = "B1"
                    frequency = 0.5
                elif length <= 10:
                    cefr = "B2"
                    frequency = 0.3
                else:
                    cefr = "C1"
                    frequency = 0.15

        # 5. Extract related words
        related_words = []
        if base != word and wordnet.synsets(base):
            related_words.append(base)
        if root_match:
            for ox_word in self.oxford_dict.keys():
                if root_match in ox_word and ox_word != word and ox_word not in related_words:
                    related_words.append(ox_word)
                    if len(related_words) >= 5:
                        break

        # Clean definitions and examples
        definitions = [d for d in definitions if d]
        examples = [e for e in examples if e]

        analysis = WordAnalysisResponse(
            word=raw_word,
            pronunciation=pronunciation,
            ipa=ipa,
            part_of_speech=part_of_speech,
            definitions=definitions,
            synonyms=synonyms,
            antonyms=antonyms,
            examples=examples,
            cefr=cefr,
            frequency=frequency,
            etymology=etymology,
            etymology_tree=etymology_tree,
            prefix_analysis=prefix_analysis,
            root_analysis=root_analysis,
            suffix_analysis=suffix_analysis,
            related_words=related_words
        )

        try:
            analysis = self.add_hindi_translations(analysis)
        except Exception as e:
            print(f"Error adding Hindi translations: {e}")

        return analysis

    def add_hindi_translations(self, analysis: WordAnalysisResponse) -> WordAnalysisResponse:
        """
        Translates English details in WordAnalysisResponse to Hindi.
        """
        from app.utils.translator import translate_to_hindi
        
        # Translate the word itself
        if analysis.word and not getattr(analysis, 'word_hindi', None):
            analysis.word_hindi = translate_to_hindi(analysis.word)
            
        # Translate part of speech
        if analysis.part_of_speech and not analysis.part_of_speech_hindi:
            analysis.part_of_speech_hindi = translate_to_hindi(analysis.part_of_speech)
            
        # Translate definitions
        if analysis.definitions and not getattr(analysis, 'definitions_hindi', None):
            analysis.definitions_hindi = [translate_to_hindi(d) for d in analysis.definitions]
            
        # Translate etymology
        if analysis.etymology and not analysis.etymology_hindi:
            analysis.etymology_hindi = translate_to_hindi(analysis.etymology)
            
        # Translate examples
        if analysis.examples and not getattr(analysis, 'examples_hindi', None):
            analysis.examples_hindi = [translate_to_hindi(ex) for ex in analysis.examples]
            
        # Translate morphological components
        if analysis.prefix_analysis:
            if not analysis.prefix_analysis.meaning_hindi:
                analysis.prefix_analysis.meaning_hindi = translate_to_hindi(analysis.prefix_analysis.meaning)
            if not analysis.prefix_analysis.role_hindi:
                analysis.prefix_analysis.role_hindi = translate_to_hindi(analysis.prefix_analysis.role)
                
        if analysis.root_analysis:
            if not analysis.root_analysis.meaning_hindi:
                analysis.root_analysis.meaning_hindi = translate_to_hindi(analysis.root_analysis.meaning)
            if not analysis.root_analysis.role_hindi:
                analysis.root_analysis.role_hindi = translate_to_hindi(analysis.root_analysis.role)
                
        if analysis.suffix_analysis:
            if not analysis.suffix_analysis.meaning_hindi:
                analysis.suffix_analysis.meaning_hindi = translate_to_hindi(analysis.suffix_analysis.meaning)
            if not analysis.suffix_analysis.role_hindi:
                analysis.suffix_analysis.role_hindi = translate_to_hindi(analysis.suffix_analysis.role)
                
        return analysis

