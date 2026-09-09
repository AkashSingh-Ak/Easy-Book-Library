// app/static/js/reader.js

let activeSessionId = null;
let currentScale = 1.0;
let pdfPageData = null; // Store current page coordinates for PDF
let loadedPages = new Set();
let cachedPdfPages = {};
let isLoadingNextPage = false;

function initReader() {
    // 1. Fetch current position & load
    fetch(`/api/books/${bookId}`)
        .then(res => res.json())
        .then(book => {
            // Estimate page number from progress percentage if page is 0
            if (book.reading_progress > 0 && book.total_pages > 0) {
                currentPage = Math.max(1, Math.round((book.reading_progress / 100) * book.total_pages));
            } else {
                currentPage = 1;
            }
            document.getElementById("page-input").value = currentPage;
            
            // Load bookmarks, TOC, and render content
            loadTOC();
            loadBookmarks();
            loadHighlights();
            loadPageContent();
            
            // Start reading session
            startReadingSession();
        });
        
    // Bind global resize handlers
    window.addEventListener("resize", () => {
        if (bookType === "pdf" || bookType === "epub") {
            redrawAllPdfPages();
        }
    });

    // Bind scroll handler on reader-canvas container
    const canvas = document.getElementById("reader-canvas");
    if (canvas) {
        canvas.addEventListener("scroll", handleScroll);
    }

    initTextSelectionHighlighting();
}

// Lets a user select a run of words on the page (dragging across the
// invisible text-span overlay) and save that selection as a highlight/note.
function initTextSelectionHighlighting() {
    const canvas = document.getElementById("reader-canvas");
    if (!canvas) return;

    canvas.addEventListener("mouseup", (e) => {
        const selectedText = (window.getSelection() || "").toString().trim();
        if (selectedText.length < 2) {
            hideSelectionHighlightButton();
            return;
        }
        showSelectionHighlightButton(selectedText, e.clientX, e.clientY);
    });

    document.addEventListener("mousedown", (e) => {
        const btn = document.getElementById("selection-highlight-btn");
        if (btn && !btn.contains(e.target)) {
            hideSelectionHighlightButton();
        }
    });
}

function showSelectionHighlightButton(text, x, y) {
    let btn = document.getElementById("selection-highlight-btn");
    if (!btn) {
        btn = document.createElement("button");
        btn.id = "selection-highlight-btn";
        btn.className = "btn btn-primary";
        document.body.appendChild(btn);
    }
    btn.innerText = "🖍 Highlight selection";
    btn.style.left = Math.max(10, x - 80) + "px";
    btn.style.top = Math.max(10, y - 45) + "px";
    btn.style.display = "block";
    btn.onclick = () => {
        addHighlightFromSelection(text);
        hideSelectionHighlightButton();
    };
}

function hideSelectionHighlightButton() {
    const btn = document.getElementById("selection-highlight-btn");
    if (btn) btn.style.display = "none";
}

function addHighlightFromSelection(text) {
    const note = prompt("Add an optional note for this highlight (leave blank for just a highlight):", "");
    if (note === null) return; // Cancelled

    fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            book_id: bookId,
            page_number: currentPage,
            text: text,
            notes: note || null,
            color: "yellow"
        })
    })
    .then(res => {
        if (!res.ok) throw new Error("Failed to save highlight");
        return res.json();
    })
    .then(() => {
        window.getSelection().removeAllRanges();
        loadHighlights();
    })
    .catch(err => console.error("Error saving highlight:", err));
}

function redrawAllPdfPages() {
    Object.keys(cachedPdfPages).forEach(pageNum => {
        drawPdfOverlay(cachedPdfPages[pageNum], parseInt(pageNum));
    });
}

function handleScroll() {
    const canvas = document.getElementById("reader-canvas");
    if (!canvas) return;

    if (bookType === "pdf" || bookType === "epub") {
        // 1. If scrolled near the bottom, load the next page in stack
        if (canvas.scrollTop + canvas.clientHeight >= canvas.scrollHeight - 400) {
            const maxLoadedPage = Math.max(...Array.from(loadedPages));
            if (maxLoadedPage < totalPages && !isLoadingNextPage) {
                isLoadingNextPage = true;
                loadNextPageStacked(maxLoadedPage + 1);
            }
        }

        // 2. Track which page is currently centered in viewport
        updateCurrentPageInViewport();
    }
}

function loadNextPageStacked(pageNum) {
    const renderer = document.getElementById("document-renderer");
    const pageWrapper = document.createElement("div");
    pageWrapper.id = `pdf-page-${pageNum}`;
    pageWrapper.className = "pdf-page-container";
    pageWrapper.style.position = "relative";
    pageWrapper.style.width = "100%";
    pageWrapper.style.background = "var(--bg-secondary)";
    pageWrapper.style.boxShadow = "var(--shadow-md)";
    pageWrapper.style.marginBottom = "2rem";
    renderer.appendChild(pageWrapper);

    fetch(`/api/books/${bookId}/page/${pageNum}`)
        .then(res => res.json())
        .then(data => {
            cachedPdfPages[pageNum] = data;
            drawPdfOverlay(data, pageNum);
            loadedPages.add(pageNum);
            isLoadingNextPage = false;
            
            // Draw any highlights present on this page
            loadHighlights();
        })
        .catch(err => {
            console.error("Error loading next page:", err);
            isLoadingNextPage = false;
        });
}

function updateCurrentPageInViewport() {
    const containers = document.querySelectorAll(".pdf-page-container");
    let closestPage = currentPage;
    let minDistance = Infinity;

    containers.forEach(c => {
        const rect = c.getBoundingClientRect();
        const viewportMiddle = window.innerHeight / 2;
        const containerMiddle = rect.top + rect.height / 2;
        const distance = Math.abs(containerMiddle - viewportMiddle);
        if (distance < minDistance) {
            minDistance = distance;
            closestPage = parseInt(c.id.replace("pdf-page-", ""));
        }
    });

    if (closestPage !== currentPage) {
        currentPage = closestPage;
        document.getElementById("page-input").value = currentPage;
        updateProgressOnBackend();
    }
}

function loadTOC() {
    fetch(`/api/books/${bookId}/toc`)
        .then(res => res.json())
        .then(toc => {
            const list = document.getElementById("toc-list");
            if (!list) return;
            list.innerHTML = "";
            
            if (toc.length === 0) {
                list.innerHTML = "<p style='color:var(--text-muted);font-size:0.85rem;'>No table of contents available.</p>";
                return;
            }

            toc.forEach(chapter => {
                const item = document.createElement("a");
                item.className = "chapter-link";
                item.innerText = chapter.title;
                item.onclick = () => {
                    jumpToPage(chapter.page_number);
                };
                list.appendChild(item);
            });
        });
}

function loadPageContent() {
    stopTts(); // Always stop speech when switching pages
    
    const renderer = document.getElementById("document-renderer");
    if (!renderer) return;
    
    renderer.innerHTML = `<div style="display:flex;align-items:center;justify-content:center;height:100%;"><p>Loading page content...</p></div>`;

    if (bookType === "pdf" || bookType === "epub") {
        loadedPages = new Set([currentPage]);
        cachedPdfPages = {};
        renderer.innerHTML = "";
        
        const pageWrapper = document.createElement("div");
        pageWrapper.id = `pdf-page-${currentPage}`;
        pageWrapper.className = "pdf-page-container";
        pageWrapper.style.position = "relative";
        pageWrapper.style.width = "100%";
        pageWrapper.style.background = "var(--bg-secondary)";
        pageWrapper.style.boxShadow = "var(--shadow-md)";
        pageWrapper.style.marginBottom = "2rem";
        renderer.appendChild(pageWrapper);

        fetch(`/api/books/${bookId}/page/${currentPage}`)
            .then(res => {
                if (!res.ok) throw new Error("Failed to load page");
                return res.json();
            })
            .then(data => {
                pdfPageData = data;
                cachedPdfPages[currentPage] = data;
                drawPdfOverlay(data, currentPage);
                updateProgressOnBackend();
                loadHighlights();
            })
            .catch(err => {
                renderer.innerHTML = `<div style="padding:2rem;color:red;">Error loading content: ${err.message}</div>`;
            });
    }
}

function renderPdfPage(data) {
    pdfPageData = data;
    drawPdfOverlay(data, currentPage);
}

function drawPdfOverlay(data, pageNum) {
    const pageContainer = document.getElementById(`pdf-page-${pageNum}`);
    if (!pageContainer) return;
    pageContainer.innerHTML = "";

    const imageWrapper = document.createElement("div");
    imageWrapper.className = "pdf-image-wrapper";
    imageWrapper.style.position = "relative";
    imageWrapper.style.width = "100%";
    imageWrapper.style.height = "100%";

    const img = document.createElement("img");
    img.src = data.image_url;
    img.style.width = "100%";
    img.style.height = "100%";
    img.style.display = "block";
    imageWrapper.appendChild(img);
    pageContainer.appendChild(imageWrapper);

    const overlay = document.createElement("div");
    overlay.className = "text-overlay";
    imageWrapper.appendChild(overlay);

    // Calculate scale factor to match container width
    const clientWidth = pageContainer.clientWidth || 800;
    const scale = (clientWidth / data.width) * currentScale;
    
    pageContainer.style.height = (data.height * scale) + "px";

    // Position transparent select spans over the page
    data.words.forEach(w => {
        const span = document.createElement("span");
        span.className = "text-span";
        span.innerText = w.text + " ";
        span.style.left = (w.x0 * scale) + "px";
        span.style.top = (w.y0 * scale) + "px";
        span.style.width = ((w.x1 - w.x0) * scale) + "px";
        span.style.height = ((w.y1 - w.y0) * scale) + "px";
        span.style.fontSize = ((w.y1 - w.y0) * scale) + "px";
        span.dataset.wordIndex = w.index;
        span.dataset.page = pageNum;
        
        span.addEventListener("dblclick", (e) => {
            const context = getSentenceContextForWord(w.index, data.sentences);
            lookupWord(w.text, w.index, e, null, context);
        });
        overlay.appendChild(span);
    });
    
    // Store current sentences global for TTS engine if active page
    if (pageNum === currentPage) {
        window.currentPageSentences = data.sentences;
        window.currentPageWords = data.words;
    }
}

function getSentenceContextForWord(wordIndex, sentences) {
    for (let s of sentences) {
        if (s.word_indices.includes(wordIndex)) {
            return {
                sentence: s.text,
                context: s.text
            };
        }
    }
    return null;
}

function prevPage() {
    if (currentPage > 1) {
        currentPage--;
        document.getElementById("page-input").value = currentPage;
        loadPageContent();
    }
}

function nextPage() {
    if (currentPage < totalPages) {
        currentPage++;
        document.getElementById("page-input").value = currentPage;
        loadPageContent();
    }
}

function jumpToPage(pageNum) {
    const val = parseInt(pageNum);
    if (val >= 1 && val <= totalPages) {
        currentPage = val;
        document.getElementById("page-input").value = currentPage;
        loadedPages = new Set([currentPage]);
        cachedPdfPages = {};
        loadPageContent();
    }
}

function updateProgressOnBackend() {
    fetch(`/api/progress/${bookId}?page_number=${currentPage}`, {
        method: "POST"
    }).catch(err => console.error("Error logging position progress:", err));
}

function adjustFont(change) {
    if (bookType === "pdf" || bookType === "epub") {
        currentScale = Math.max(0.7, Math.min(2.0, currentScale + (change * 0.1)));
        redrawAllPdfPages();
    }
}

function toggleFullscreen() {
    const container = document.querySelector(".reader-container");
    if (!document.fullscreenElement) {
        container.requestFullscreen().catch(err => console.error(err));
    } else {
        document.exitFullscreen();
    }
}

// Session loggers
function startReadingSession() {
    fetch("/api/progress/session/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ book_id: bookId })
    })
    .then(res => res.json())
    .then(session => {
        activeSessionId = session.session_id;
    });

    // Close session on unload
    window.addEventListener("beforeunload", endReadingSession);
}

function endReadingSession() {
    if (activeSessionId) {
        navigator.sendBeacon(`/api/progress/session/end/${activeSessionId}`);
    }
}

function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    
    // Find target
    const btn = Array.from(document.querySelectorAll(".tab-btn")).find(b => b.innerText.toLowerCase().includes(tabId === 'toc' ? 'contents' : tabId));
    if (btn) btn.classList.add("active");
    
    const content = document.getElementById(`tab-${tabId}`);
    if (content) content.classList.add("active");
}

// Bookmarks CRUD
function loadBookmarks() {
    fetch(`/api/bookmarks/${bookId}`)
        .then(res => res.json())
        .then(bookmarks => {
            const list = document.getElementById("bookmarks-list");
            if (!list) return;
            list.innerHTML = "";
            
            if (bookmarks.length === 0) {
                list.innerHTML = "<p style='color:var(--text-muted);font-size:0.85rem;padding:0.5rem;'>No bookmarks saved.</p>";
                return;
            }
            
            bookmarks.forEach(b => {
                const item = document.createElement("div");
                item.style = "display:flex;justify-content:space-between;align-items:center;padding:0.4rem 0.5rem;background:rgba(255,255,255,0.03);border-radius:4px;margin-bottom:0.25rem;";
                item.innerHTML = `
                    <span onclick="jumpToPage(${b.page_number})" style="cursor:pointer;font-size:0.9rem;flex:1;">
                        📌 Page ${b.page_number} ${b.title ? '- ' + escapeHtml(b.title) : ''}
                    </span>
                    <button onclick="deleteBookmark(${b.id})" style="background:none;border:none;color:#ef4444;cursor:pointer;font-size:0.85rem;">✕</button>
                `;
                list.appendChild(item);
            });
        });
}

function addCurrentBookmark() {
    const title = prompt("Enter a title for this bookmark (optional):");
    if (title === null) return; // Cancelled
    
    fetch("/api/bookmarks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            book_id: bookId,
            page_number: currentPage,
            title: title || `Page ${currentPage}`
        })
    })
    .then(res => res.json())
    .then(() => {
        loadBookmarks();
    })
    .catch(err => console.error("Error adding bookmark:", err));
}

function deleteBookmark(id) {
    if (!confirm("Remove this bookmark?")) return;
    
    fetch(`/api/bookmarks/${id}`, { method: "DELETE" })
        .then(() => loadBookmarks())
        .catch(err => console.error(err));
}

// Highlights & Notes manager
function loadHighlights() {
    fetch(`/api/notes/${bookId}`)
        .then(res => res.json())
        .then(notes => {
            const list = document.getElementById("highlights-list");
            if (!list) return;
            list.innerHTML = "";
            
            // Extract and redraw highlights on active page
            drawVisualHighlightsOnPage(notes);

            if (notes.length === 0) {
                list.innerHTML = "<p style='color:var(--text-muted);font-size:0.85rem;padding:0.5rem;'>No notes or highlights saved.</p>";
                return;
            }

            notes.forEach(n => {
                const item = document.createElement("div");
                item.style = "background:rgba(0,0,0,0.15);padding:0.75rem;border-radius:6px;margin-bottom:0.5rem;border-left:3px solid " + (n.color || 'yellow');
                item.innerHTML = `
                    <div style="display:flex;justify-content:space-between;font-size:0.8rem;color:var(--text-muted);margin-bottom:0.25rem;">
                        <span onclick="jumpToPage(${n.page_number})" style="cursor:pointer;">Page ${n.page_number}</span>
                        <button onclick="deleteHighlight(${n.id})" style="background:none;border:none;color:#ef4444;cursor:pointer;">✕</button>
                    </div>
                    <blockquote style="font-size:0.85rem;font-style:italic;color:var(--text-secondary);margin-bottom:0.5rem;">"${escapeHtml(n.text)}"</blockquote>
                    ${n.notes ? `<p style="font-size:0.85rem;color:var(--text-primary);"><strong style="color:var(--accent-color)">Note:</strong> ${escapeHtml(n.notes)}</p>` : ''}
                `;
                list.appendChild(item);
            });
        });
}

function drawVisualHighlightsOnPage(notes) {
    // PDF/EPUB page highlight overlay drawing helper
    if ((bookType !== "pdf" && bookType !== "epub") || !pdfPageData) return;
    
    // Clear old visual highlights
    document.querySelectorAll(".highlight-overlay").forEach(el => el.remove());
    
    const pageNotes = notes.filter(n => n.page_number === currentPage);
    const renderer = document.querySelector(".pdf-image-wrapper");
    if (!renderer) return;
    
    const clientWidth = document.getElementById("document-renderer").clientWidth;
    const scale = (clientWidth / pdfPageData.width) * currentScale;

    pageNotes.forEach(n => {
        // If sentence index matches
        if (n.sentence_index !== null && window.currentPageSentences && window.currentPageSentences[n.sentence_index]) {
            const sentence = window.currentPageSentences[n.sentence_index];
            sentence.word_indices.forEach(wIdx => {
                const w = window.currentPageWords[wIdx];
                if (w) {
                    const el = document.createElement("div");
                    el.className = `highlight-overlay ${n.color || 'yellow'}`;
                    el.style.position = "absolute";
                    el.style.left = (w.x0 * scale) + "px";
                    el.style.top = (w.y0 * scale) + "px";
                    el.style.width = ((w.x1 - w.x0) * scale) + "px";
                    el.style.height = ((w.y1 - w.y0) * scale) + "px";
                    el.style.pointerEvents = "none";
                    renderer.appendChild(el);
                }
            });
        }
    });
}

function deleteHighlight(id) {
    if (!confirm("Delete this highlight/note?")) return;
    fetch(`/api/notes/${id}`, { method: "DELETE" })
        .then(() => loadHighlights())
        .catch(err => console.error(err));
}

// Inside book full-text search
function searchInsideBook() {
    const query = document.getElementById("book-search-input").value.trim();
    const list = document.getElementById("search-results-list");
    if (!list) return;
    if (!query) {
        list.innerHTML = "";
        return;
    }

    list.innerHTML = "<p style='color:var(--text-muted);font-size:0.85rem;'>Searching...</p>";

    fetch(`/api/search/${bookId}?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(results => {
            list.innerHTML = "";
            if (results.length === 0) {
                list.innerHTML = "<p style='color:var(--text-muted);font-size:0.85rem;'>No matches found.</p>";
                return;
            }

            results.forEach(r => {
                const item = document.createElement("div");
                item.style = "background:rgba(255,255,255,0.02);border:1px solid var(--border-color);padding:0.5rem;border-radius:4px;cursor:pointer;";
                item.onclick = () => jumpToPage(r.page_number);
                
                item.innerHTML = `
                    <div style="font-size:0.8rem;font-weight:600;color:var(--accent-color);margin-bottom:0.25rem;">
                        Page/Chapter ${r.page_number} ${r.chapter_title ? ' - ' + escapeHtml(r.chapter_title) : ''}
                    </div>
                    <p style="font-size:0.85rem;color:var(--text-secondary);">${escapeHtml(r.context)}</p>
                `;
                list.appendChild(item);
            });
        })
        .catch(err => {
            list.innerHTML = `<p style="color:red;font-size:0.85rem;">Error: ${err.message}</p>`;
        });
}

