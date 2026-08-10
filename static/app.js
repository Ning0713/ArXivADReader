(function () {
    "use strict";

    const STORAGE_KEY = "adpaper_favorites_v1";
    const cartCount = document.getElementById("paperCartCount");
    const cartIds = document.getElementById("paperCartIds");
    const cartStatus = document.getElementById("paperCartStatus");
    const copyButton = document.getElementById("paperCartCopyBtn");
    const clearButton = document.getElementById("paperCartClearBtn");
    const toggleButtons = Array.from(document.querySelectorAll(".cart-toggle-btn"));

    function normalizeCart(value) {
        if (!Array.isArray(value)) return [];
        const seen = new Set();
        return value.filter(function (item) {
            if (!item || typeof item.id !== "string" || seen.has(item.id)) return false;
            seen.add(item.id);
            return true;
        });
    }

    function loadCart() {
        try {
            return normalizeCart(JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]"));
        } catch (_) {
            return [];
        }
    }

    let cart = loadCart();
    let statusTimer = null;

    function saveCart() {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
        } catch (_) {
            showCartStatus("收藏保存失败，浏览器存储不可用", true);
        }
    }

    function showCartStatus(message, isError) {
        if (!cartStatus) return;
        cartStatus.textContent = message;
        cartStatus.style.color = isError ? "#b91c1c" : "";
        window.clearTimeout(statusTimer);
        statusTimer = window.setTimeout(function () {
            cartStatus.textContent = "";
            cartStatus.style.color = "";
        }, 2600);
    }

    function hasFavorite(id) {
        return cart.some(function (item) { return item.id === id; });
    }

    function renderCart() {
        if (!cartCount || !cartIds) return;
        cartCount.textContent = String(cart.length);
        cartIds.replaceChildren();
        if (!cart.length) {
            const empty = document.createElement("span");
            empty.className = "cart-empty";
            empty.textContent = "暂无收藏";
            cartIds.appendChild(empty);
        } else {
            cart.forEach(function (item) {
                const chip = document.createElement("span");
                chip.className = "cart-chip";
                const code = document.createElement("code");
                code.textContent = item.id;
                const remove = document.createElement("button");
                remove.type = "button";
                remove.className = "cart-chip-remove";
                remove.dataset.removeId = item.id;
                remove.setAttribute("aria-label", "移除 " + item.id);
                remove.textContent = "×";
                chip.append(code, remove);
                cartIds.appendChild(chip);
            });
        }
        toggleButtons.forEach(function (button) {
            const active = hasFavorite(button.dataset.arxivId || "");
            button.textContent = active ? "取消收藏" : "加入收藏";
            button.classList.toggle("in-cart", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
        });
    }

    toggleButtons.forEach(function (button) {
        button.addEventListener("click", function () {
            const id = (button.dataset.arxivId || "").trim();
            if (!id) return;
            if (hasFavorite(id)) {
                cart = cart.filter(function (item) { return item.id !== id; });
                showCartStatus("已移除 " + id, false);
            } else {
                cart.push({
                    id: id,
                    title: (button.dataset.paperTitle || "").trim(),
                    date: (button.dataset.paperDate || "").trim(),
                    tags: (button.dataset.paperTags || "").split("|").filter(Boolean),
                    addedAt: new Date().toISOString()
                });
                showCartStatus("已收藏 " + id, false);
            }
            saveCart();
            renderCart();
        });
    });

    if (cartIds) {
        cartIds.addEventListener("click", function (event) {
            const id = event.target && event.target.dataset ? event.target.dataset.removeId : "";
            if (!id) return;
            cart = cart.filter(function (item) { return item.id !== id; });
            saveCart();
            renderCart();
        });
    }

    if (copyButton) {
        copyButton.addEventListener("click", async function () {
            if (!cart.length) {
                showCartStatus("收藏清单为空", true);
                return;
            }
            const text = cart.map(function (item) { return item.id; }).join("\n");
            try {
                await navigator.clipboard.writeText(text);
                showCartStatus("已复制 " + cart.length + " 个 ID", false);
            } catch (_) {
                const area = document.createElement("textarea");
                area.value = text;
                document.body.appendChild(area);
                area.select();
                document.execCommand("copy");
                area.remove();
                showCartStatus("已复制 " + cart.length + " 个 ID", false);
            }
        });
    }

    if (clearButton) {
        clearButton.addEventListener("click", function () {
            if (!cart.length) return showCartStatus("收藏清单已经为空", true);
            if (!window.confirm("确认清空全部收藏吗？")) return;
            cart = [];
            saveCart();
            renderCart();
            showCartStatus("已清空收藏", false);
        });
    }

    renderCart();

    const searchPanel = document.getElementById("paperSearch");
    const tagFilter = document.getElementById("paperTagFilter");
    const keywordInput = document.getElementById("paperKeywordSearch");
    const searchStatus = document.getElementById("paperSearchStatus");
    const searchResults = document.getElementById("paperSearchResults");
    let indexPromise = null;

    function normalized(value) {
        return String(value || "").normalize("NFKC").toLocaleLowerCase();
    }

    function loadSearchIndex() {
        if (!searchPanel) return Promise.resolve([]);
        if (!indexPromise) {
            searchStatus.textContent = "Loading…";
            indexPromise = fetch(searchPanel.dataset.indexUrl, { cache: "force-cache" })
                .then(function (response) {
                    if (!response.ok) throw new Error("Search index unavailable");
                    return response.json();
                })
                .then(function (value) { return Array.isArray(value.items) ? value.items : []; })
                .catch(function () {
                    searchStatus.textContent = "搜索索引加载失败";
                    return [];
                });
        }
        return indexPromise;
    }

    function resultText(item) {
        return [item.id, item.title, item.title_zh, (item.authors || []).join(" "), item.abstract,
            item.abstract_zh, (item.tags || []).join(" ")].join(" ");
    }

    async function runSearch() {
        if (!tagFilter || !keywordInput || !searchResults || !searchStatus) return;
        const tag = tagFilter.value;
        const query = normalized(keywordInput.value.trim());
        searchResults.replaceChildren();
        if (!tag && !query) {
            searchStatus.textContent = "";
            return;
        }
        const items = await loadSearchIndex();
        const matches = items.filter(function (item) {
            const tagMatch = !tag || (item.tags || []).includes(tag);
            const keywordMatch = !query || normalized(resultText(item)).includes(query);
            return tagMatch && keywordMatch;
        });
        searchStatus.textContent = matches.length + " results";
        const fragment = document.createDocumentFragment();
        matches.forEach(function (item) {
            const link = document.createElement("a");
            link.className = "search-result";
            link.href = item.url;
            link.textContent = item.title_zh || item.title || item.id;
            const meta = document.createElement("span");
            meta.className = "search-result-meta";
            meta.textContent = item.date + " · " + item.id + " · " + (item.tags || []).join(" / ");
            link.appendChild(meta);
            fragment.appendChild(link);
        });
        searchResults.appendChild(fragment);
    }

    if (tagFilter && keywordInput) {
        let debounceTimer = null;
        tagFilter.addEventListener("change", runSearch);
        keywordInput.addEventListener("focus", loadSearchIndex);
        keywordInput.addEventListener("input", function () {
            window.clearTimeout(debounceTimer);
            debounceTimer = window.setTimeout(runSearch, 160);
        });
        document.querySelectorAll("[data-search-tag]").forEach(function (button) {
            button.addEventListener("click", function () {
                tagFilter.value = button.dataset.searchTag || "";
                runSearch();
                searchPanel.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        });
    }

    const sidebar = document.getElementById("sidebar");
    const sidebarToggle = document.getElementById("sidebarToggle");
    const sidebarOverlay = document.getElementById("sidebarOverlay");

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove("open");
        if (sidebarOverlay) sidebarOverlay.classList.remove("active");
    }

    if (sidebar && sidebarToggle && sidebarOverlay) {
        sidebarToggle.addEventListener("click", function () {
            sidebar.classList.toggle("open");
            sidebarOverlay.classList.toggle("active");
        });
        sidebarOverlay.addEventListener("click", closeSidebar);
        sidebar.querySelectorAll(".sidebar-link").forEach(function (link) {
            link.addEventListener("click", closeSidebar);
        });
    }

    const navLinks = Array.from(document.querySelectorAll(".sidebar-link[data-section]"));
    function updateReadingProgress() {
        const readLine = window.scrollY + window.innerHeight * 0.7;
        navLinks.forEach(function (link) {
            const section = document.getElementById(link.dataset.section);
            const bar = link.querySelector(".progress-bar");
            if (!section || !bar) return;
            const top = section.offsetTop;
            const progress = Math.max(0, Math.min(100, ((readLine - top) / section.offsetHeight) * 100));
            bar.style.height = progress + "%";
            const rect = section.getBoundingClientRect();
            link.classList.toggle("active", rect.top <= window.innerHeight * 0.4 && rect.bottom > 100);
        });
    }

    const backToTop = document.querySelector(".back-to-top");
    function updateScrollControls() {
        if (backToTop) backToTop.classList.toggle("visible", window.scrollY > 480);
        updateReadingProgress();
    }
    window.addEventListener("scroll", updateScrollControls, { passive: true });
    if (backToTop) {
        backToTop.addEventListener("click", function () {
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    }
    updateScrollControls();
})();

