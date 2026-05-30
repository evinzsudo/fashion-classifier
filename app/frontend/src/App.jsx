import { useState, useEffect, useCallback, useRef } from "react";
import { fetchGarments, fetchFilters, uploadGarment } from "./api.js";
import FilterPanel from "./components/FilterPanel.jsx";
import SearchBar from "./components/SearchBar.jsx";
import ImageGrid from "./components/ImageGrid.jsx";
import GarmentModal from "./components/GarmentModal.jsx";

const EMPTY_FILTERS = {
  garment_type: "",
  style: "",
  material: "",
  color_palette: "",
  pattern: "",
  season: "",
  occasion: "",
  consumer_profile: "",
  location_context: "",
};

export default function App() {
  const [garments, setGarments] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [activeFilters, setActiveFilters] = useState(EMPTY_FILTERS);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedGarment, setSelectedGarment] = useState(null);
  const [toast, setToast] = useState(null);

  const fileInputRef = useRef(null);
  const searchTimer = useRef(null);
  const [debouncedSearch, setDebouncedSearch] = useState("");

  // Debounce search
  useEffect(() => {
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => setDebouncedSearch(search), 300);
    return () => clearTimeout(searchTimer.current);
  }, [search]);

  const loadGarments = useCallback(async () => {
    setLoading(true);
    try {
      const params = { ...activeFilters, search: debouncedSearch };
      const data = await fetchGarments(params);
      setGarments(data);
    } catch (e) {
      showToast(e.message, "error");
    } finally {
      setLoading(false);
    }
  }, [activeFilters, debouncedSearch]);

  useEffect(() => {
    loadGarments();
  }, [loadGarments]);

  useEffect(() => {
    fetchFilters().then(setFilterOptions).catch(() => {});
  }, [garments]);

  function showToast(message, type = "success") {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  }

  async function handleUpload(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    setUploading(true);
    showToast("Uploading and classifying…", "success");
    try {
      await uploadGarment(file);
      showToast("Garment classified and saved.", "success");
      await loadGarments();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      setUploading(false);
    }
  }

  function handleFilterChange(key, value) {
    setActiveFilters((prev) => ({ ...prev, [key]: value }));
  }

  function handleGarmentUpdate(updated) {
    setGarments((prev) => prev.map((g) => (g.id === updated.id ? updated : g)));
    if (selectedGarment?.id === updated.id) setSelectedGarment(updated);
  }

  const activeCount = Object.values(activeFilters).filter(Boolean).length;

  return (
    <div className="app">
      <header className="header">
        <h1>Fashion Classifier</h1>
        <div className="header-spacer" />
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          className="upload-input"
          onChange={handleUpload}
        />
        <button
          className="upload-btn"
          disabled={uploading}
          onClick={() => fileInputRef.current?.click()}
        >
          {uploading ? (
            <>
              <span className="spinner" /> Classifying…
            </>
          ) : (
            "+ Upload Garment"
          )}
        </button>
      </header>

      <div className="body">
        <FilterPanel
          filterOptions={filterOptions}
          activeFilters={activeFilters}
          onFilterChange={handleFilterChange}
        />

        <main className="main">
          <SearchBar value={search} onChange={setSearch} />

          <div className="grid-header">
            <span className="grid-count">
              {loading ? "Loading…" : `${garments.length} garment${garments.length !== 1 ? "s" : ""}${activeCount ? ` · ${activeCount} filter${activeCount !== 1 ? "s" : ""} active` : ""}`}
            </span>
          </div>

          <ImageGrid
            garments={garments}
            loading={loading}
            onCardClick={setSelectedGarment}
          />
        </main>
      </div>

      {selectedGarment && (
        <GarmentModal
          garment={selectedGarment}
          onClose={() => setSelectedGarment(null)}
          onUpdate={handleGarmentUpdate}
        />
      )}

      {toast && (
        <div className={`toast ${toast.type}`}>{toast.message}</div>
      )}
    </div>
  );
}
