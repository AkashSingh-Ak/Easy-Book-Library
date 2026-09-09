// app/static/js/vocab.js

let selectedWordData = null; // Store current lookup payload
let currentDetailWord = null;

// Initialize word popup listeners on reader
function initWordSelectionPopup() {
    // Hide popup when clicking anywhere outside it
    document.addEventListener("mousedown", (e) => {
        const popup = document.getElementById("dict-popup");
        if (popup && popup.style.display === "flex" && !popup.contains(e.target)) {
            closeDictionaryPopup();
        }
    });
}

function lookupWord(word, wordIdx, event, iframeOffset = null, textContext = null) {
    window.lastLookedUpWordIndex = wordIdx;
    const popup = document.getElementById("dict-popup");
    if (!popup) return;

    // Clean word
    const cleaned = word.replace(/[.,\/#!$%\^&\*;:{}=\-_`~()?"']/g,"").trim();
    if (!cleaned || cleaned.length < 2) return;

    // Retrieve position
    let x = event.clientX;
    let y = event.clientY;

    if (iframeOffset) {
        // Adjust clientX/Y coordinates if double clicked inside EPUB iframe
        x += iframeOffset.left;
        y += iframeOffset.top;
    }

    // Call backend endpoint to trigger dictionary lookup and auto-save word
    let url = `/api/vocabulary/lookup/${encodeURIComponent(cleaned)}?book_id=${bookId}&page_number=${currentPage}`;
    if (textContext) {
        if (textContext.sentence) url += `&sentence=${encodeURIComponent(textContext.sentence)}`;
        if (textContext.context) url += `&context=${encodeURIComponent(textContext.context)}`;
    }

    fetch(url)
        .then(res => {
            if (!res.ok) throw new Error("Word lookup failed");
            return res.json();
        })
        .then(data => {
            selectedWordData = data;
            
            // Populate popup elements
            document.getElementById("dict-word").innerText = data.word;
            
            const dictHindiEl = document.getElementById("dict-word-hindi");
            if (dictHindiEl) {
                if (isHindiEnabled() && data.word_hindi) {
                    dictHindiEl.innerText = data.word_hindi;
                    dictHindiEl.style.display = "block";
                } else {
                    dictHindiEl.style.display = "none";
                }
            }

            document.getElementById("dict-ipa").innerText = data.ipa || "";
            document.getElementById("dict-pos").innerText = data.part_of_speech || "";
            document.getElementById("dict-cefr").innerText = data.cefr || "B1";

            let meaningText = data.definitions[0] || "No offline definition available.";
            if (isHindiEnabled() && data.definitions_hindi && data.definitions_hindi[0]) {
                meaningText += `\n(${data.definitions_hindi[0]})`;
            }
            document.getElementById("dict-meaning").innerText = meaningText;
            
            // Adjust popup coordinates to float above selection
            popup.style.display = "flex";
            const popupWidth = popup.clientWidth || 320;
            const popupHeight = popup.clientHeight || 200;
            
            // Prevent going off screen
            let left = x - (popupWidth / 2);
            let top = y - popupHeight - 15;
            
            if (left < 10) left = 10;
            if (left + popupWidth > window.innerWidth) left = window.innerWidth - popupWidth - 10;
            if (top < 10) top = y + 15; // Show below selection if it would go off top
            
            popup.style.left = left + "px";
            popup.style.top = top + "px";
            
            // Log word lookup in local reader list to refresh notes panel if visible
            loadHighlights();
            updateSaveWordButtonState();
        })
        .catch(err => console.error("Error during dictionary lookup:", err));
}

function updateSaveWordButtonState() {
    const btn = document.getElementById("save-word-btn");
    if (!btn) return;
    
    if (selectedWordData && selectedWordData.is_saved) {
        btn.innerText = "🔎 Full Analysis";
        btn.onclick = openVocabularyDeckDetails;
    } else {
        btn.innerText = "➕ Add to Vocabulary";
        btn.onclick = saveWordToVocabulary;
    }
}

function saveWordToVocabulary() {
    if (!selectedWordData) return;
    
    let url = `/api/vocabulary/save?word=${encodeURIComponent(selectedWordData.word)}&book_id=${bookId}&page_number=${currentPage}`;
    
    fetch(url, { method: "POST" })
        .then(res => {
            if (!res.ok) throw new Error("Failed to save word");
            return res.json();
        })
        .then(data => {
            selectedWordData.is_saved = true;
            updateSaveWordButtonState();
            loadHighlights();
        })
        .catch(err => console.error("Error saving word:", err));
}

function closeDictionaryPopup() {
    const popup = document.getElementById("dict-popup");
    if (popup) popup.style.display = "none";
}

function speakCurrentWord() {
    if (selectedWordData && selectedWordData.word) {
        const u = new SpeechSynthesisUtterance(selectedWordData.word);
        window.speechSynthesis.speak(u);
    }
}

function openVocabularyDeckDetails() {
    // Open full analysis details page
    if (selectedWordData && selectedWordData.word) {
        let url = `/vocabulary?word=${encodeURIComponent(selectedWordData.word)}`;
        if (typeof bookId !== 'undefined' && bookId) {
            url += `&book_id=${encodeURIComponent(bookId)}`;
        }
        window.open(url, "_blank");
    }
}

// ------------------------------------------------------------------
// SAVED VOCABULARY PAGE LOGIC
// ------------------------------------------------------------------

function loadVocabDeck() {
    const search = document.getElementById("vocab-search")?.value || "";
    const status = document.getElementById("vocab-filter-status")?.value || "";
    const sortBy = document.getElementById("vocab-sort-by")?.value || "date_desc";

    let url = `/api/vocabulary?sort_by=${sortBy}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (status) url += `&learning_status=${status}`;

    fetch(url)
        .then(res => res.json())
        .then(words => {
            renderVocabDeck(words);
            
            // If there's a word query param in URL, auto-load that word
            const urlParams = new URLSearchParams(window.location.search);
            const autoWord = urlParams.get("word");
            if (autoWord && words.some(w => w.word.toLowerCase() === autoWord.toLowerCase())) {
                selectVocabWord(autoWord);
                // Clear URL param after loading once
                window.history.replaceState({}, document.title, window.location.pathname);
            } else if (words.length > 0 && !currentDetailWord) {
                // Auto-select first word in list
                selectVocabWord(words[0].word);
            }
        })
        .catch(err => console.error("Error fetching vocab deck:", err));
}

function renderVocabDeck(words) {
    const container = document.getElementById("vocab-deck-container");
    if (!container) return;
    container.innerHTML = "";

    if (words.length === 0) {
        container.innerHTML = `<p style="text-align:center;padding:2rem;color:var(--text-muted);">No vocabulary words found.</p>`;
        return;
    }

    words.forEach(w => {
        const card = document.createElement("div");
        card.className = `vocab-word-card ${currentDetailWord === w.word ? 'active' : ''}`;
        card.onclick = () => selectVocabWord(w.word);
        
        let wordHindiText = "";
        try {
            if (isHindiEnabled() && w.definition_json) {
                const details = JSON.parse(w.definition_json);
                if (details.word_hindi) {
                    wordHindiText = `<div style="font-size:0.9rem;color:var(--accent-color);margin-top:0.1rem;margin-bottom:0.25rem;">${details.word_hindi}</div>`;
                }
            }
        } catch (e) {
            console.error("Error parsing definition_json for card:", e);
        }
        
        card.innerHTML = `
            <div style="display:flex;justify-content:between;align-items:center;margin-bottom:0.25rem;">
                <div style="display:flex;flex-direction:column;">
                    <strong style="font-size:1.1rem;color:var(--text-primary);">${w.word}</strong>
                    ${wordHindiText}
                </div>
                <span class="vocab-status-tag status-${w.learning_status.replace(" ", "_")}" style="margin-left:auto;">${w.learning_status}</span>
            </div>
            <p style="font-size:0.85rem;color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${w.meaning}</p>
        `;
        container.appendChild(card);
    });
}

function selectVocabWord(word) {
    currentDetailWord = word;
    
    // Highlight card in list
    document.querySelectorAll(".vocab-word-card").forEach(c => {
        const title = c.querySelector("strong").innerText.toLowerCase();
        c.classList.toggle("active", title === word.toLowerCase());
    });

    fetch(`/api/vocabulary/word/${encodeURIComponent(word)}`)
        .then(res => res.json())
        .then(vocab => {
            displayWordDetails(vocab);
        })
        .catch(err => console.error("Error loading word details:", err));
}

// Fills in one prefix/root/suffix row of the "Word Structure Decomposition"
// panel, or hides it when that word has no such component.
function renderMorphItem(elementId, analysis) {
    const el = document.getElementById(elementId);
    if (!analysis) {
        el.style.display = "none";
        return;
    }

    el.style.display = "flex";
    let text = `${analysis.component} (meaning: ${analysis.meaning}`;
    if (isHindiEnabled() && analysis.meaning_hindi) {
        text += ` / ${analysis.meaning_hindi}`;
    }
    text += `) [${analysis.role}`;
    if (isHindiEnabled() && analysis.role_hindi) {
        text += ` / ${analysis.role_hindi}`;
    }
    text += `]`;
    el.querySelector(".morph-text").innerText = text;
}

function displayWordDetails(vocab) {
    // Show details container, hide empty state
    document.getElementById("vocab-empty-state").style.display = "none";
    document.getElementById("vocab-details-content").style.display = "flex";

    // Load full JSON data serialized from lookup
    const details = JSON.parse(vocab.definition_json);

    // Update the corresponding card in the list to show the updated meaning (with Hindi translation) and word_hindi
    document.querySelectorAll(".vocab-word-card").forEach(c => {
        const titleEl = c.querySelector("strong");
        if (titleEl && titleEl.innerText.toLowerCase() === vocab.word.toLowerCase()) {
            const descEl = c.querySelector("p");
            if (descEl && vocab.meaning) {
                descEl.innerText = vocab.meaning;
            }
            if (isHindiEnabled() && details.word_hindi) {
                let hindiEl = titleEl.parentNode.querySelector("div");
                if (!hindiEl) {
                    hindiEl = document.createElement("div");
                    hindiEl.style.fontSize = "0.9rem";
                    hindiEl.style.color = "var(--accent-color)";
                    hindiEl.style.marginTop = "0.1rem";
                    hindiEl.style.marginBottom = "0.25rem";
                    titleEl.parentNode.appendChild(hindiEl);
                }
                hindiEl.innerText = details.word_hindi;
            }
        }
    });

    document.getElementById("detail-word").innerText = vocab.word;

    const hindiWordEl = document.getElementById("detail-word-hindi");
    if (hindiWordEl) {
        if (isHindiEnabled() && details.word_hindi) {
            hindiWordEl.innerText = details.word_hindi;
            hindiWordEl.style.display = "block";
        } else {
            hindiWordEl.style.display = "none";
        }
    }
    document.getElementById("detail-ipa").innerText = details.ipa || "";
    let posText = details.part_of_speech || "";
    if (isHindiEnabled() && details.part_of_speech_hindi) {
        posText += ` (${details.part_of_speech_hindi})`;
    }
    document.getElementById("detail-pos").innerText = posText;
    document.getElementById("detail-cefr").innerText = details.cefr || "B1";
    document.getElementById("detail-views").innerText = `Times viewed: ${vocab.times_viewed} | Times searched: ${vocab.times_searched}`;
    document.getElementById("detail-status").value = vocab.learning_status;
    document.getElementById("detail-notes").value = vocab.personal_notes || "";
    
    // Render definitions list
    const defsList = document.getElementById("detail-definitions");
    defsList.innerHTML = "";
    details.definitions.forEach((d, idx) => {
        const li = document.createElement("li");
        li.style.marginBottom = "0.75rem";
        
        // English definition
        const engSpan = document.createElement("div");
        engSpan.innerText = d;
        li.appendChild(engSpan);
        
        // Hindi translation
        if (isHindiEnabled() && details.definitions_hindi && details.definitions_hindi[idx]) {
            const hindiSpan = document.createElement("div");
            hindiSpan.style.color = "var(--accent-color)";
            hindiSpan.style.fontSize = "0.9rem";
            hindiSpan.style.marginTop = "0.15rem";
            hindiSpan.innerText = details.definitions_hindi[idx];
            li.appendChild(hindiSpan);
        }
        defsList.appendChild(li);
    });

    // Render morphology details (prefix / root / suffix all share the same layout)
    renderMorphItem("detail-prefix", details.prefix_analysis);
    renderMorphItem("detail-root", details.root_analysis);
    renderMorphItem("detail-suffix", details.suffix_analysis);

    // Hide entire block if no affixes are present
    const morphContainer = document.getElementById("detail-prefix").parentNode.parentNode;
    if (!details.prefix_analysis && !details.root_analysis && !details.suffix_analysis) {
        morphContainer.style.display = "none";
    } else {
        morphContainer.style.display = "block";
    }

    // Related words
    const relatedContainer = document.getElementById("detail-related");
    relatedContainer.innerHTML = "";
    if (details.related_words && details.related_words.length > 0) {
        details.related_words.forEach(rw => {
            const span = document.createElement("span");
            span.style = "background:rgba(255,255,255,0.06);padding:0.25rem 0.5rem;border-radius:4px;font-size:0.85rem;cursor:pointer;border:1px solid var(--border-color);";
            span.innerText = rw;
            span.onclick = () => selectVocabWord(rw);
            relatedContainer.appendChild(span);
        });
    } else {
        relatedContainer.innerHTML = `<span style="color:var(--text-muted);font-size:0.85rem;">None identified.</span>`;
    }

    // Etymology description
    let etymHTML = details.etymology || "No historical etymology trace found.";
    if (isHindiEnabled() && details.etymology_hindi) {
        etymHTML += `<div style="color: var(--accent-color); font-size: 0.9rem; margin-top: 0.25rem;">${details.etymology_hindi}</div>`;
    }
    document.getElementById("detail-etymology").innerHTML = etymHTML;
    
    // Etymology tree structure visualizer
    const treeEl = document.getElementById("detail-etymology-tree");
    if (details.etymology_tree) {
        treeEl.style.display = "block";
        treeEl.innerText = details.etymology_tree;
    } else {
        treeEl.style.display = "none";
    }

    // Synonyms & Antonyms
    const synsContainer = document.getElementById("detail-synonyms");
    synsContainer.innerHTML = "";
    if (details.synonyms && details.synonyms.length > 0) {
        details.synonyms.forEach(s => {
            const span = document.createElement("span");
            span.style = "background:rgba(16,185,129,0.1);color:#10b981;padding:0.2rem 0.5rem;border-radius:4px;font-size:0.85rem;";
            span.innerText = s;
            synsContainer.appendChild(span);
        });
    } else {
        synsContainer.innerHTML = `<span style="color:var(--text-muted);font-size:0.85rem;">None found.</span>`;
    }

    const antsContainer = document.getElementById("detail-antonyms");
    antsContainer.innerHTML = "";
    if (details.antonyms && details.antonyms.length > 0) {
        details.antonyms.forEach(a => {
            const span = document.createElement("span");
            span.style = "background:rgba(239,68,68,0.1);color:#ef4444;padding:0.2rem 0.5rem;border-radius:4px;font-size:0.85rem;";
            span.innerText = a;
            antsContainer.appendChild(span);
        });
    } else {
        antsContainer.innerHTML = `<span style="color:var(--text-muted);font-size:0.85rem;">None found.</span>`;
    }
}

function updateWordStatus() {
    if (!currentDetailWord) return;
    const status = document.getElementById("detail-status").value;

    fetch(`/api/vocabulary/word/${encodeURIComponent(currentDetailWord)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ learning_status: status })
    })
    .then(res => res.json())
    .then(vocab => {
        loadVocabDeck(); // Refresh sidebar list
    })
    .catch(err => console.error("Error updating word status:", err));
}

function saveWordNotes() {
    if (!currentDetailWord) return;
    const notes = document.getElementById("detail-notes").value;
    const statusEl = document.getElementById("save-status");
    statusEl.innerText = "Saving...";

    fetch(`/api/vocabulary/word/${encodeURIComponent(currentDetailWord)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ personal_notes: notes })
    })
    .then(res => res.json())
    .then(vocab => {
        statusEl.innerText = "Notes saved locally.";
    })
    .catch(err => {
        console.error("Error saving word notes:", err);
        statusEl.innerText = "Save failed.";
    });
}

function deleteCurrentWord() {
    if (!currentDetailWord) return;
    if (!confirm(`Are you sure you want to delete "${currentDetailWord}" from your vocabulary deck?`)) {
        return;
    }

    fetch(`/api/vocabulary/word/${encodeURIComponent(currentDetailWord)}`, {
        method: "DELETE"
    })
    .then(res => res.json())
    .then(() => {
        currentDetailWord = null;
        document.getElementById("vocab-details-content").style.display = "none";
        document.getElementById("vocab-empty-state").style.display = "flex";
        loadVocabDeck();
    })
    .catch(err => console.error("Error deleting vocab word:", err));
}

// Check for book_id in URL or referrer to show "Back to Reading" option
function initBackToReadingOption() {
    const urlParams = new URLSearchParams(window.location.search);
    let bookIdParam = urlParams.get("book_id");
    
    // If not in URL, try parsing from referrer
    if (!bookIdParam && document.referrer) {
        try {
            const refUrl = new URL(document.referrer);
            if (refUrl.pathname.startsWith("/reader/")) {
                const parts = refUrl.pathname.split("/");
                bookIdParam = parts[parts.length - 1];
            }
        } catch (e) {
            console.error("Failed to parse referrer URL:", e);
        }
    }
    
    if (bookIdParam) {
        const container = document.getElementById("back-to-reading-container");
        const link = document.getElementById("back-to-reading-link");
        if (container && link) {
            link.href = `/reader/${encodeURIComponent(bookIdParam)}`;
            container.style.display = "block";
        }
    }
}
