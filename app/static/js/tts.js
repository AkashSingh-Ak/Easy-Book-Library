// app/static/js/tts.js

let synth = window.speechSynthesis;
let voices = [];
let currentUtterance = null;
let activeSentenceIdx = 0;
let isSpeaking = false;
let isPaused = false;

function initTtsEngine() {
    if (!synth) {
        console.warn("Speech Synthesis is not supported in this browser.");
        return;
    }

    // Load available voices (requires event handling as they load asynchronously)
    loadVoices();
    if (synth.onvoiceschanged !== undefined) {
        synth.onvoiceschanged = loadVoices;
    }

    // Read settings from backend to configure sliders
    fetch("/api/settings")
        .then(res => res.json())
        .then(settings => {
            document.getElementById("tts-rate").value = settings.speech_rate;
            document.getElementById("rate-val").innerText = settings.speech_rate + "x";
            
            document.getElementById("tts-pitch").value = settings.speech_pitch;
            document.getElementById("pitch-val").innerText = settings.speech_pitch;
            
            document.getElementById("tts-volume").value = settings.speech_volume;
            document.getElementById("volume-val").innerText = Math.round(settings.speech_volume * 100) + "%";
            
            // Set preferred voice name (will match in loadVoices when loaded)
            window.preferredVoiceName = settings.speech_voice;
        });
}

function loadVoices() {
    voices = synth.getVoices();
    const select = document.getElementById("tts-voice-select");
    if (!select) return;
    select.innerHTML = "";

    voices.forEach(voice => {
        const option = document.createElement("option");
        option.value = voice.name;
        option.innerText = `${voice.name} (${voice.lang}) ${voice.localService ? '[Local]' : ''}`;
        
        if (window.preferredVoiceName && voice.name === window.preferredVoiceName) {
            option.selected = true;
        } else if (!window.preferredVoiceName && voice.lang.startsWith("en")) {
            option.selected = true; // Fallback to English default
        }
        select.appendChild(option);
    });
}

function saveTtsPreferences() {
    const rate = parseFloat(document.getElementById("tts-rate").value);
    const pitch = parseFloat(document.getElementById("tts-pitch").value);
    const volume = parseFloat(document.getElementById("tts-volume").value);
    const voice = document.getElementById("tts-voice-select").value;

    fetch("/api/settings", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            theme: document.body.className.replace("theme-", ""),
            font_size: parseInt(localStorage.getItem("reader-font-size") || "16"),
            margins: 15,
            line_spacing: 1.5,
            paragraph_spacing: 1.0,
            speech_rate: rate,
            speech_pitch: pitch,
            speech_volume: volume,
            speech_voice: voice
        })
    }).catch(err => console.error("Error saving settings:", err));
}

function toggleTtsPlay() {
    if (isSpeaking && !isPaused) {
        // Pause
        synth.pause();
        isPaused = true;
        document.getElementById("tts-play-btn").innerText = "▶️ Resume";
    } else if (isSpeaking && isPaused) {
        // Resume
        synth.resume();
        isPaused = false;
        document.getElementById("tts-play-btn").innerText = "⏸️ Pause";
    } else {
        // Start from beginning of current page
        activeSentenceIdx = 0;
        speakSentence();
    }
}

function speakSentence() {
    if (!window.currentPageSentences || window.currentPageSentences.length === 0) return;
    
    // Safety check
    if (activeSentenceIdx >= window.currentPageSentences.length) {
        // End of page, advance to next page if auto scroll enabled
        if (document.getElementById("tts-autoscroll").checked && currentPage < totalPages) {
            nextPage();
            // Wait slightly for page to load and trigger play automatically
            setTimeout(() => {
                activeSentenceIdx = 0;
                speakSentence();
            }, 1000);
        } else {
            stopTts();
        }
        return;
    }

    const sentence = window.currentPageSentences[activeSentenceIdx];
    let textToSpeak = "";
    
    if (bookType === "pdf") {
        textToSpeak = sentence.text;
    } else {
        textToSpeak = sentence.text;
    }

    currentUtterance = new SpeechSynthesisUtterance(textToSpeak);
    
    // Set parameters
    const rate = parseFloat(document.getElementById("tts-rate").value);
    const pitch = parseFloat(document.getElementById("tts-pitch").value);
    const volume = parseFloat(document.getElementById("tts-volume").value);
    const voiceName = document.getElementById("tts-voice-select").value;
    
    currentUtterance.rate = rate;
    currentUtterance.pitch = pitch;
    currentUtterance.volume = volume;
    
    const selectedVoice = voices.find(v => v.name === voiceName);
    if (selectedVoice) {
        currentUtterance.voice = selectedVoice;
    }

    // Set highlights on start
    currentUtterance.onstart = () => {
        isSpeaking = true;
        isPaused = false;
        document.getElementById("tts-play-btn").innerText = "⏸️ Pause";
        
        clearSentenceHighlights();
        highlightActiveSentence(sentence);
        autoScrollToSentence(sentence);
    };

    // Listen to boundary changes (for word highlighting if local engine supports it)
    currentUtterance.onboundary = (event) => {
        if (event.name === "word") {
            // Option to perform word level highlight if boundaries are active
        }
    };

    currentUtterance.onend = () => {
        clearSentenceHighlights();
        activeSentenceIdx++;
        speakSentence();
    };

    currentUtterance.onerror = (e) => {
        console.error("TTS error:", e);
        stopTts();
    };

    synth.speak(currentUtterance);
}

function stopTts() {
    synth.cancel();
    clearSentenceHighlights();
    isSpeaking = false;
    isPaused = false;
    activeSentenceIdx = 0;
    const playBtn = document.getElementById("tts-play-btn");
    if (playBtn) playBtn.innerText = "▶️ Play";
}

function ttsNextSentence() {
    if (isSpeaking) {
        synth.cancel();
        activeSentenceIdx++;
        speakSentence();
    }
}

function ttsPrevSentence() {
    if (isSpeaking) {
        synth.cancel();
        activeSentenceIdx = Math.max(0, activeSentenceIdx - 1);
        speakSentence();
    }
}

function highlightActiveSentence(sentence) {
    if (bookType === "pdf" || bookType === "epub") {
        // PDF/EPUB word-indices mapping
        sentence.word_indices.forEach(idx => {
            const span = document.querySelector(`.text-span[data-word-index="${idx}"]`);
            if (span) span.classList.add("spoken-sentence-highlight");
        });
    }
}

function clearSentenceHighlights() {
    if (bookType === "pdf" || bookType === "epub") {
        document.querySelectorAll(".text-span").forEach(s => s.classList.remove("spoken-sentence-highlight"));
    }
}

function autoScrollToSentence(sentence) {
    if (!document.getElementById("tts-autoscroll").checked) return;

    if (bookType === "pdf" || bookType === "epub") {
        const canvas = document.getElementById("reader-canvas");
        const firstIdx = sentence.word_indices[0];
        const span = document.querySelector(`.text-span[data-word-index="${firstIdx}"]`);
        if (span && canvas) {
            const topOffset = span.offsetTop;
            canvas.scrollTo({
                top: topOffset - (canvas.clientHeight / 2),
                behavior: "smooth"
            });
        }
    }
}

// "Read from here" handler to start speech at a selected word index
window.readFromHere = function() {
    // 1. Close lookup popup if visible
    if (typeof closeDictionaryPopup === 'function') {
        closeDictionaryPopup();
    }

    // 2. Stop current speech
    synth.cancel();

    // 3. Find sentence containing window.lastLookedUpWordIndex
    if (typeof window.lastLookedUpWordIndex !== 'undefined' && window.lastLookedUpWordIndex !== null && window.currentPageSentences) {
        const wordIdx = window.lastLookedUpWordIndex;
        let targetSentIdx = 0;
        for (let i = 0; i < window.currentPageSentences.length; i++) {
            const sent = window.currentPageSentences[i];
            if (sent.word_indices && sent.word_indices.includes(wordIdx)) {
                targetSentIdx = i;
                break;
            }
        }
        
        // 4. Set active sentence index and start speaking
        activeSentenceIdx = targetSentIdx;
        isSpeaking = true;
        isPaused = false;
        speakSentence();
    }
};
