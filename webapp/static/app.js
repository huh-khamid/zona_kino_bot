// Telegram WebApp and Cinema Frontend Logic

document.addEventListener("DOMContentLoaded", () => {
    // 1. Initialize Telegram Mini App SDK
    const tg = window.Telegram?.WebApp;
    if (tg) {
        tg.ready();
        tg.expand();
        try {
            tg.setHeaderColor('#0a0c10');
            tg.setBackgroundColor('#0a0c10');
        } catch (e) {}
    }

    // State
    let currentCategory = "all";
    let moviesList = [];
    let searchDebounceTimer = null;
    let currentOpenedMovie = null;

    // DOM Elements
    const searchInput = document.getElementById("searchInput");
    const clearSearchBtn = document.getElementById("clearSearchBtn");
    const categoryTabs = document.getElementById("categoryTabs");
    const moviesGrid = document.getElementById("moviesGrid");
    const loadingState = document.getElementById("loadingState");
    const emptyState = document.getElementById("emptyState");
    const heroSection = document.getElementById("heroSection");
    const heroTitle = document.getElementById("heroTitle");
    const heroDesc = document.getElementById("heroDescription");
    const heroRating = document.getElementById("heroRating");
    const heroYear = document.getElementById("heroYear");
    const heroGenres = document.getElementById("heroGenres");
    const heroBackdrop = document.getElementById("heroBackdrop");
    const heroWatchBtn = document.getElementById("heroWatchBtn");
    const sectionTitle = document.getElementById("sectionTitle");
    const resultsCount = document.getElementById("resultsCount");
    const userStatusText = document.getElementById("userStatusText");
    const userBadge = document.getElementById("userBadge");

    // Modal Elements
    const playerModal = document.getElementById("playerModal");
    const closeModalBtn = document.getElementById("closeModalBtn");
    const modalTitle = document.getElementById("modalMovieTitle");
    const modalRating = document.getElementById("modalMovieRating");
    const modalYear = document.getElementById("modalMovieYear");
    const modalDuration = document.getElementById("modalMovieDuration");
    const modalGenres = document.getElementById("modalMovieGenres");
    const modalDesc = document.getElementById("modalMovieDesc");
    const kinoboxContainer = document.getElementById("kinoboxContainer");

    // Paywall Modal
    const paywallModal = document.getElementById("paywallModal");
    const paywallBtn = document.getElementById("paywallBtn");

    // Check user subscription status
    const userId = tg?.initDataUnsafe?.user?.id;
    if (userId) {
        checkSubscription(userId);
    }

    async function checkSubscription(uid) {
        try {
            const resp = await fetch(`/api/user/status?user_id=${uid}`);
            if (resp.ok) {
                const data = await resp.json();
                if (data.is_subscribed) {
                    userStatusText.textContent = "VIP Активен";
                    userBadge.className = "user-badge vip";
                } else {
                    userStatusText.textContent = "Демо доступ";
                    userBadge.className = "user-badge demo";
                }
            }
        } catch (e) {
            console.error("Error verifying user subscription:", e);
        }
    }

    if (paywallBtn) {
        paywallBtn.addEventListener("click", () => {
            if (tg) {
                tg.close();
            }
        });
    }

    // Load initial catalog
    loadCatalog(currentCategory);

    // Category Tabs Click
    categoryTabs.addEventListener("click", (e) => {
        const btn = e.target.closest(".cat-pill");
        if (!btn) return;

        document.querySelectorAll(".cat-pill").forEach(p => p.classList.remove("active"));
        btn.classList.add("active");

        currentCategory = btn.dataset.category;
        searchInput.value = "";
        clearSearchBtn.style.display = "none";
        heroSection.style.display = currentCategory === "all" ? "flex" : "none";
        sectionTitle.textContent = getSectionTitle(currentCategory);
        
        loadCatalog(currentCategory);
    });

    function getSectionTitle(cat) {
        switch (cat) {
            case "movie": return "Фильмы";
            case "series": return "Сериалы";
            case "cartoon": return "Мультфильмы";
            case "anime": return "Аниме";
            default: return "Популярное сейчас";
        }
    }

    // Fetch Catalog from Backend
    async function loadCatalog(category) {
        showLoading(true);
        try {
            const resp = await fetch(`/api/movies/catalog?category=${category}`);
            const data = await resp.json();
            moviesList = data.movies || [];
            
            renderMovies(moviesList);
            if (category === "all" && moviesList.length > 0) {
                const featured = moviesList.find(m => m.featured) || moviesList[0];
                setupHero(featured);
            }
        } catch (err) {
            console.error("Error loading catalog:", err);
        } finally {
            showLoading(false);
        }
    }

    // Setup Featured Hero
    function setupHero(movie) {
        if (!movie) return;
        heroTitle.textContent = movie.title;
        heroDesc.textContent = movie.description;
        heroRating.textContent = `⭐ ${movie.rating}`;
        heroYear.textContent = movie.year;
        heroGenres.textContent = movie.genres.join(" • ");
        heroBackdrop.style.backgroundImage = `url('${movie.backdrop || movie.poster}')`;

        heroWatchBtn.onclick = () => openPlayerModal(movie);
    }

    // Search Input Listener with Debounce
    searchInput.addEventListener("input", (e) => {
        const query = e.target.value.trim();
        
        if (query.length > 0) {
            clearSearchBtn.style.display = "block";
            heroSection.style.display = "none";
            sectionTitle.textContent = `Результаты поиска: "${query}"`;
        } else {
            clearSearchBtn.style.display = "none";
            heroSection.style.display = currentCategory === "all" ? "flex" : "none";
            sectionTitle.textContent = getSectionTitle(currentCategory);
            renderMovies(moviesList);
            return;
        }

        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
            performSearch(query);
        }, 300);
    });

    clearSearchBtn.addEventListener("click", () => {
        searchInput.value = "";
        clearSearchBtn.style.display = "none";
        heroSection.style.display = currentCategory === "all" ? "flex" : "none";
        sectionTitle.textContent = getSectionTitle(currentCategory);
        renderMovies(moviesList);
    });

    // Search Request
    async function performSearch(query) {
        showLoading(true);
        try {
            const resp = await fetch(`/api/movies/search?q=${encodeURIComponent(query)}`);
            const data = await resp.json();
            renderMovies(data.results || []);
        } catch (err) {
            console.error("Search error:", err);
        } finally {
            showLoading(false);
        }
    }

    // Render Movie Cards
    function renderMovies(list) {
        moviesGrid.innerHTML = "";
        resultsCount.textContent = list.length > 0 ? `${list.length} найдено` : "";

        if (list.length === 0) {
            emptyState.style.display = "block";
            return;
        }
        emptyState.style.display = "none";

        list.forEach(movie => {
            const card = document.createElement("div");
            card.className = "movie-card";
            card.innerHTML = `
                <div class="card-poster-wrap">
                    <img class="card-poster" src="${movie.poster}" alt="${movie.title}" loading="lazy" onerror="this.src='https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=600&auto=format&fit=crop'">
                    <span class="card-rating-badge">⭐ ${movie.rating}</span>
                </div>
                <div class="card-info">
                    <h3 class="card-title" title="${movie.title}">${movie.title}</h3>
                    <div class="card-meta">
                        <span>${movie.year}</span>
                        <span>${movie.genres ? movie.genres[0] : 'Кино'}</span>
                    </div>
                </div>
            `;
            card.addEventListener("click", () => openPlayerModal(movie));
            moviesGrid.appendChild(card);
        });
    }

    // Open Movie & Kinobox Player Modal
    function openPlayerModal(movie) {
        currentOpenedMovie = movie;
        modalTitle.textContent = movie.title;
        modalRating.textContent = `⭐ ${movie.rating}`;
        modalYear.textContent = movie.year;
        modalDuration.textContent = movie.duration || "120 мин.";
        modalGenres.textContent = movie.genres ? movie.genres.join(", ") : "";
        modalDesc.textContent = movie.description || "Описание фильма отсутствует.";

        // Clear previous player
        kinoboxContainer.innerHTML = "";

        // Open Modal
        playerModal.classList.add("active");
        document.body.style.overflow = "hidden";

        // Setup Telegram BackButton
        if (tg?.BackButton) {
            tg.BackButton.show();
            tg.BackButton.onClick(closePlayerModal);
        }

        // Initialize Kinobox Player Embed
        setTimeout(() => {
            if (window.Kinobox) {
                new Kinobox('.kinobox_player', {
                    search: {
                        kinopoisk: movie.kp_id || "",
                        title: movie.title
                    },
                    players: ['alloha', 'kodik', 'collaps', 'videocdn', 'vdb']
                }).init();
            } else {
                kinoboxContainer.innerHTML = `
                    <div style="padding: 40px 20px; text-align: center; color: #94a3b8;">
                        <p>Загрузка видеоплеера...</p>
                    </div>
                `;
            }
        }, 100);
    }

    function closePlayerModal() {
        playerModal.classList.remove("active");
        document.body.style.overflow = "auto";
        kinoboxContainer.innerHTML = ""; // Stop video playback

        if (tg?.BackButton) {
            tg.BackButton.hide();
        }
    }

    closeModalBtn.addEventListener("click", closePlayerModal);

    // Close on overlay backdrop click
    playerModal.addEventListener("click", (e) => {
        if (e.target === playerModal) {
            closePlayerModal();
        }
    });

    function showLoading(show) {
        loadingState.style.display = show ? "block" : "none";
        if (show) emptyState.style.display = "none";
    }
});
