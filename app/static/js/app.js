// app/static/js/app.js

let currentViewMode = "grid"; // 'grid' or 'list'

function setupDragAndDrop() {
    const dropzone = document.getElementById("dropzone");
    if (!dropzone) return;

    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "var(--accent-color)";
            dropzone.style.background = "rgba(59, 130, 246, 0.08)";
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.style.borderColor = "var(--border-color)";
            dropzone.style.background = "var(--bg-glass)";
        }, false);
    });

    dropzone.addEventListener("drop", (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });
}

function handleFileSelect(event) {
    const files = event.target.files;
    handleFiles(files);
}

function handleFiles(files) {
    if (!files.length) return;
    
    // Upload files sequentially
    Array.from(files).forEach(file => {
        uploadBookFile(file);
    });
}

function uploadBookFile(file) {
    const formData = new FormData();
    formData.append("file", file);

    // Show a loading toast or alert
    const dropzone = document.getElementById("dropzone");
    const originalContent = dropzone.innerHTML;
    dropzone.innerHTML = `<h3>Uploading "${file.name}"...</h3><p style='color:var(--text-muted)'>Please wait while the file is processed.</p>`;

    fetch("/api/books/upload", {
        method: "POST",
        body: formData
    })
    .then(res => {
        if (!res.ok) throw new Error("Upload failed.");
        return res.json();
    })
    .then(book => {
        // Reset dropzone UI
        dropzone.innerHTML = originalContent;
        setupDragAndDrop(); // Re-bind events
        
        // Refresh collection
        fetchBooks();
    })
    .catch(err => {
        alert("Failed to upload book: " + err.message);
        dropzone.innerHTML = originalContent;
        setupDragAndDrop();
    });
}

function fetchBooks() {
    const search = document.getElementById("library-search")?.value || "";
    const type = document.getElementById("filter-type")?.value || "";
    const status = document.getElementById("filter-status")?.value || "";
    const sortBy = document.getElementById("sort-by")?.value || "added_date_desc";

    let url = `/api/books?sort_by=${sortBy}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (type) url += `&filter_type=${type}`;
    if (status) url += `&filter_status=${status}`;

    fetch(url)
        .then(res => res.json())
        .then(books => {
            renderBooks(books);
        })
        .catch(err => console.error("Error loading library books:", err));
}

function setViewMode(mode) {
    currentViewMode = mode;
    
    // Toggle active state on buttons
    document.getElementById("view-grid-btn")?.classList.toggle("active", mode === "grid");
    document.getElementById("view-list-btn")?.classList.toggle("active", mode === "list");
    
    // Toggle container classes
    const container = document.getElementById("books-container");
    if (container) {
        if (mode === "grid") {
            container.className = "books-grid";
        } else {
            container.className = "books-list";
        }
    }
    
    // Re-fetch books to render in the correct container layout
    fetchBooks();
}

function renderBooks(books) {
    const container = document.getElementById("books-container");
    if (!container) return;
    container.innerHTML = "";

    if (books.length === 0) {
        container.innerHTML = `
            <div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: var(--text-muted);">
                <h3>No books found in your library</h3>
                <p style="margin-top: 0.5rem;">Use the drag & drop zone above to add PDF or EPUB files.</p>
            </div>
        `;
        return;
    }

    books.forEach(book => {
        const coverUrl = book.cover_path || "/static/covers/default_cover.png";
        const progressPercent = book.reading_progress || 0;
        const fileSizeMb = (book.file_size / (1024 * 1024)).toFixed(1);
        const title = escapeHtml(book.title);
        const author = escapeHtml(book.author || "Unknown");

        if (currentViewMode === "grid") {
            // Render Grid Card
            const card = document.createElement("div");
            card.className = "book-card";
            card.innerHTML = `
                <div class="book-cover-container" onclick="openBook('${book.id}')" style="cursor: pointer;">
                    <img class="book-cover" src="${coverUrl}" alt="Cover" onerror="this.src='/static/covers/default_cover.png'">
                    <span class="book-badge">${book.file_type}</span>
                    <div class="book-progress-bar" style="width: ${progressPercent}%"></div>
                </div>
                <div class="book-details">
                    <h4 class="book-title" onclick="openBook('${book.id}')" style="cursor: pointer;" title="${title}">${title}</h4>
                    <span class="book-author">${author}</span>
                    <div class="book-meta">
                        <span>${progressPercent > 0 ? progressPercent + '%' : 'Unread'}</span>
                        <span>${fileSizeMb} MB</span>
                    </div>
                    <button class="btn btn-danger" style="margin-top: 0.5rem; width: 100%; padding: 0.25rem; font-size: 0.8rem; justify-content: center;" onclick="deleteBook('${book.id}', event)">Delete</button>
                </div>
            `;
            container.appendChild(card);
        } else {
            // Render List Row
            const row = document.createElement("div");
            row.className = "book-list-item";
            row.innerHTML = `
                <img class="book-list-cover" src="${coverUrl}" alt="Cover" onerror="this.src='/static/covers/default_cover.png'">
                <div class="book-list-info" onclick="openBook('${book.id}')" style="cursor: pointer;">
                    <h4 class="book-title" style="margin-bottom: 0.25rem;">${title}</h4>
                    <span class="book-author">${author}</span>
                </div>
                <div style="flex: 0.5; color: var(--text-muted); font-size: 0.85rem;">
                    Format: <span style="text-transform: uppercase; font-weight: 600;">${book.file_type}</span>
                </div>
                <div class="book-list-progress-wrapper">
                    <div style="display: flex; justify-content: space-between; font-size: 0.8rem;">
                        <span>Progress</span>
                        <span>${progressPercent}%</span>
                    </div>
                    <div class="progress-track">
                        <div class="progress-fill" style="width: ${progressPercent}%"></div>
                    </div>
                </div>
                <div class="book-list-actions">
                    <button class="btn btn-secondary" onclick="openBook('${book.id}')">Read</button>
                    <button class="btn btn-danger" onclick="deleteBook('${book.id}', event)">Delete</button>
                </div>
            `;
            container.appendChild(row);
        }
    });
}

function openBook(bookId) {
    window.location.href = `/reader/${bookId}`;
}

function deleteBook(bookId, event) {
    event.stopPropagation();
    if (!confirm("Are you sure you want to delete this book? This will permanently delete bookmarks, notes, and highlights.")) {
        return;
    }

    fetch(`/api/books/${bookId}`, {
        method: "DELETE"
    })
    .then(res => res.json())
    .then(data => {
        fetchBooks();
    })
    .catch(err => alert("Failed to delete book: " + err.message));
}
