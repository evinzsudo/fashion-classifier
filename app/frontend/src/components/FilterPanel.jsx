const FILTER_LABELS = {
  garment_type: "Type",
  style: "Style",
  material: "Material",
  color_palette: "Color",
  pattern: "Pattern",
  season: "Season",
  occasion: "Occasion",
  consumer_profile: "Consumer",
  location_context: "Location",
};

export default function FilterPanel({ filterOptions, activeFilters, onFilterChange }) {
  const hasActive = Object.values(activeFilters).some(Boolean);
  const keys = Object.keys(FILTER_LABELS);

  return (
    <aside className="sidebar">
      <div className="sidebar-title">Filters</div>
      {keys.map((key) => {
        const options = filterOptions[key] || [];
        if (!options.length) return null;
        return (
          <div key={key} className="filter-group">
            <div className="filter-group-label">{FILTER_LABELS[key]}</div>
            {options.map((val) => (
              <label
                key={val}
                className={`filter-option${activeFilters[key] === val ? " active" : ""}`}
              >
                <input
                  type="radio"
                  name={key}
                  value={val}
                  checked={activeFilters[key] === val}
                  onChange={() =>
                    onFilterChange(
                      key,
                      activeFilters[key] === val ? "" : val
                    )
                  }
                />
                {val}
              </label>
            ))}
          </div>
        );
      })}
      {hasActive && (
        <button
          className="clear-filters-btn"
          onClick={() => {
            keys.forEach((k) => onFilterChange(k, ""));
          }}
        >
          Clear all filters
        </button>
      )}
    </aside>
  );
}
