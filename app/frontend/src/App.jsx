import { useState, useEffect, useCallback, useRef } from "react";
import { fetchGarments, fetchFilters, uploadGarment } from "./api.js";
import FilterPanel from "./components/FilterPanel.jsx";
import SearchBar from "./components/SearchBar.jsx";
import ImageGrid from "./components/ImageGrid.jsx";
import GarmentModal from "./components/GarmentModal.jsx";
import UploadModal from "./components/UploadModal.jsx";

const EMPTY_FILTERS = {
  garment_type: "", style: "", material: "", color_palette: "",
  pattern: "", season: "", occasion: "", consumer_profile: "",
  location_context: "", continent: "", country: "", city: "",
  designer: "", year: "", month: "", trend_keyword: "",
};

export default function App() {
  const [garments, setGarments] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [activeFilters, setActiveFilters] = useState(EMPTY_FILTERS);
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [pendingFile, setPendingFile] = useState(null);
  const [selectedGarment, setSelectedGarment] = useState(null);
  const [isDragging, setIsDragging] = useState(false);
  const [toasts, setToasts] = useState([]);

  const fileInputRef = useRef(null);
  const searchRef = useRef(null);
  const searchTimer = useRef(null);
  const dragCount = useRef(0);

  // ── Search debounce ───────────────────────────────────────────────────────
  useEffect(() => {
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(searchTimer.current);
  }, [search]);

  // ── Data loading ──────────────────────────────────────────────────────────
  const loadGarments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchGarments({ ...activeFilters, search: debouncedSearch });
      setGarments(data);
    } catch (e) {
      showToast(e.message || "Failed to load garments.", "error");
    } finally {
      setLoading(false);
    }
  }, [activeFilters, debouncedSearch]);

  useEffect(() => { loadGarments(); }, [loadGarments]);

  useEffect(() => {
    fetchFilters().then(setFilterOptions).catch(() => {});
  }, [garments]);

  // ── Toast system ──────────────────────────────────────────────────────────
  function showToast(message, type = "success") {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => removeToast(id), 5000);
  }
  function removeToast(id) {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }

  // ── Keyboard shortcuts ────────────────────────────────────────────────────
  useEffect(() => {
    function onKeyDown(e) {
      // "/" focuses search, unless already in a text field or modal is open
      if (
        e.key === "/" &&
        !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName) &&
        !pendingFile &&
        !selectedGarment
      ) {
        e.preventDefault();
        searchRef.current?.focus();
      }
      if (e.key === "Escape") {
        if (selectedGarment) setSelectedGarment(null);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [pendingFile, selectedGarment]);

  // ── Drag-and-drop ─────────────────────────────────────────────────────────
  useEffect(() => {
    function onDragEnter(e) {
      if (Array.from(e.dataTransfer?.types || []).includes("Files")) {
        dragCount.current++;
        setIsDragging(true);
      }
    }
    function onDragLeave() {
      dragCount.current = Math.max(0, dragCount.current - 1);
      if (dragCount.current === 0) setIsDragging(false);
    }
    function onDragOver(e) { e.preventDefault(); }
    function onDrop(e) {
      e.preventDefault();
      dragCount.current = 0;
      setIsDragging(false);
      const file = e.dataTransfer?.files?.[0];
      if (!file) return;
      if (!file.type.startsWith("image/")) {
        showToast("Please drop an image file (JPEG, PNG, WebP, or GIF).", "error");
        return;
      }
      setPendingFile(file);
    }
    document.addEventListener("dragenter", onDragEnter);
    document.addEventListener("dragleave", onDragLeave);
    document.addEventListener("dragover", onDragOver);
    document.addEventListener("drop", onDrop);
    return () => {
      document.removeEventListener("dragenter", onDragEnter);
      document.removeEventListener("dragleave", onDragLeave);
      document.removeEventListener("dragover", onDragOver);
      document.removeEventListener("drop", onDrop);
    };
  }, []);

  // ── Upload flow ───────────────────────────────────────────────────────────
  function handleFileSelect(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setPendingFile(file);
  }

  async function handleUploadConfirm(metadata) {
    try {
      await uploadGarment(pendingFile, metadata);
      setPendingFile(null);
      showToast("Garment classified and saved.", "success");
      await loadGarments();
    } catch (err) {
      showToast(err.message || "Upload failed.", "error");
      throw err; // re-throw so UploadModal can enter error state
    }
  }

  // ── Filters ───────────────────────────────────────────────────────────────
  function handleFilterChange(key, value) {
    setActiveFilters((prev) => ({ ...prev, [key]: value }));
  }

  function clearAllFilters() {
    setActiveFilters(EMPTY_FILTERS);
    setSearch("");
  }

  function handleGarmentUpdate(updated) {
    setGarments((prev) => prev.map((g) => (g.id === updated.id ? updated : g)));
    if (selectedGarment?.id === updated.id) setSelectedGarment(updated);
  }

  const hasActiveFilters =
    Object.values(activeFilters).some(Boolean) || !!debouncedSearch;

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <button
          className="hamburger-btn"
          onClick={() => setSidebarOpen((v) => !v)}
          aria-label="Toggle filters"
        >
          ☰
        </button>
        <div className="header-logo">
          <div className="header-logo-icon">✦</div>
          <h1>Fashion Classifier</h1>
        </div>
        <div className="header-spacer" />
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          className="upload-input"
          onChange={handleFileSelect}
        />
        <button
          className="upload-btn"
          onClick={() => fileInputRef.current?.click()}
        >
          + Upload Garment
        </button>
      </header>

      {/* ── Body ── */}
      <div className="body">
        {/* Mobile sidebar backdrop */}
        {sidebarOpen && (
          <div
            className="sidebar-backdrop"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <FilterPanel
          filterOptions={filterOptions}
          activeFilters={activeFilters}
          onFilterChange={handleFilterChange}
          garmentCount={loading ? undefined : garments.length}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
        />

        <main className="main">
          <SearchBar
            ref={searchRef}
            value={search}
            onChange={setSearch}
          />
          <ImageGrid
            garments={garments}
            loading={loading}
            onCardClick={setSelectedGarment}
            searchTerm={debouncedSearch}
            hasFilters={hasActiveFilters}
            onClearFilters={clearAllFilters}
          />
        </main>
      </div>

      {/* ── Drag overlay ── */}
      {isDragging && (
        <div className="drag-overlay" aria-hidden="true">
          <div className="drag-overlay-inner">
            <div className="drag-icon">📸</div>
            <div className="drag-text">Drop image to classify</div>
          </div>
        </div>
      )}

      {/* ── Modals ── */}
      {pendingFile && (
        <UploadModal
          file={pendingFile}
          onConfirm={handleUploadConfirm}
          onCancel={() => setPendingFile(null)}
        />
      )}
      {selectedGarment && (
        <GarmentModal
          garment={selectedGarment}
          onClose={() => setSelectedGarment(null)}
          onUpdate={handleGarmentUpdate}
        />
      )}

      {/* ── Toast stack ── */}
      <div className="toast-container" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.type}`}>
            <span>{t.message}</span>
            <button className="toast-dismiss" onClick={() => removeToast(t.id)}>×</button>
          </div>
        ))}
      </div>
    </div>
  );
}
