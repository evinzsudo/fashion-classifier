import { useState } from "react";

const MONTH_NAMES = {
  "01": "January",  "02": "February", "03": "March",
  "04": "April",    "05": "May",      "06": "June",
  "07": "July",     "08": "August",   "09": "September",
  "10": "October",  "11": "November", "12": "December",
};

const FILTER_DEFS = [
  { key: "garment_type",     label: "Garment Type",     type: "radio" },
  { key: "style",            label: "Style",            type: "radio" },
  { key: "material",         label: "Material",         type: "radio" },
  { key: "color_palette",    label: "Color",            type: "radio" },
  { key: "pattern",          label: "Pattern",          type: "radio" },
  { key: "season",           label: "Season",           type: "radio" },
  { key: "occasion",         label: "Occasion",         type: "radio" },
  { key: "consumer_profile", label: "Consumer Profile", type: "radio" },
  { key: "location_context", label: "Location Context", type: "radio" },
  { key: "trend_keyword",    label: "Trend Keyword",    type: "text",
    placeholder: "e.g. oversized, Y2K…" },
  { divider: "Context" },
  { key: "continent",        label: "Continent",        type: "radio" },
  { key: "country",          label: "Country",          type: "radio" },
  { key: "city",             label: "City",             type: "radio" },
  { key: "designer",         label: "Designer",         type: "radio" },
  { key: "year",             label: "Year",             type: "radio" },
  { key: "month",            label: "Month",            type: "radio" },
];

const ALL_FILTER_KEYS = FILTER_DEFS.filter((d) => d.key).map((d) => d.key);

function CollapsibleFilter({ def, options, active, onFilterChange, isExpanded, onToggle }) {
  const { key, label, type, placeholder } = def;
  const count = type === "radio" ? options.length : null;
  const hasActive = !!active;

  if (type === "radio" && !options.length) return null;

  return (
    <div className={`cfilter${hasActive ? " cfilter-active" : ""}`}>
      <button className="cfilter-header" onClick={onToggle}>
        <span className="cfilter-header-left">
          <span className="cfilter-label">
            {label}
            {count !== null && count > 0 && (
              <span className="cfilter-count"> ({count})</span>
            )}
          </span>
          {hasActive && (
            <span className="cfilter-badge">1</span>
          )}
        </span>
        <span className="cfilter-chevron">{isExpanded ? "▾" : "▸"}</span>
      </button>

      {isExpanded && (
        <div className="cfilter-body">
          {type === "radio" && (
            <div className="filter-group">
              {options.map((val) => {
                const display = key === "month" ? (MONTH_NAMES[val] ?? val) : val;
                return (
                  <label
                    key={val}
                    className={`filter-option${active === val ? " active" : ""}`}
                  >
                    <input
                      type="radio"
                      name={key}
                      value={val}
                      checked={active === val}
                      onChange={() => {}}
                      onClick={() => onFilterChange(key, active === val ? "" : val)}
                    />
                    {display}
                  </label>
                );
              })}
            </div>
          )}

          {type === "text" && (
            <div className="trend-keyword-wrap">
              <input
                type="text"
                className="trend-keyword-input"
                placeholder={placeholder}
                value={active || ""}
                onChange={(e) => onFilterChange(key, e.target.value)}
              />
              {active && (
                <button
                  className="trend-keyword-clear"
                  onClick={() => onFilterChange(key, "")}
                >
                  ×
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function FilterPanel({
  filterOptions,
  activeFilters,
  onFilterChange,
  garmentCount,
  sidebarOpen,
  onToggleSidebar,
}) {
  const [expandedKeys, setExpandedKeys] = useState(new Set(["garment_type"]));

  function toggleKey(key) {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  }

  const totalActive = ALL_FILTER_KEYS.filter((k) => activeFilters[k]).length;
  const hasActive = totalActive > 0;

  return (
    <aside className={`sidebar${sidebarOpen ? "" : " sidebar-collapsed"}`}>
      <div className="sidebar-header">
        <button
          className="sidebar-toggle-btn"
          onClick={onToggleSidebar}
          title={sidebarOpen ? "Collapse filters" : "Expand filters"}
        >
          {sidebarOpen ? "‹" : "›"}
        </button>

        {sidebarOpen && (
          <>
            <span className="sidebar-title">
              Filters
              {totalActive > 0 && (
                <span className="filter-active-badge">{totalActive}</span>
              )}
            </span>
            <span className="sidebar-spacer" />
            {typeof garmentCount === "number" && (
              <span className="filter-result-count">{garmentCount} results</span>
            )}
          </>
        )}
      </div>

      {sidebarOpen && (
        <div className="sidebar-content">
          {FILTER_DEFS.map((def, i) => {
            if (def.divider) {
              return (
                <div key={`divider-${i}`} className="filter-section-divider">
                  <span className="filter-section-divider-label">{def.divider}</span>
                </div>
              );
            }
            return (
              <CollapsibleFilter
                key={def.key}
                def={def}
                options={filterOptions[def.key] || []}
                active={activeFilters[def.key] || ""}
                onFilterChange={onFilterChange}
                isExpanded={expandedKeys.has(def.key)}
                onToggle={() => toggleKey(def.key)}
              />
            );
          })}

          {hasActive && (
            <button
              className="clear-filters-btn"
              onClick={() => ALL_FILTER_KEYS.forEach((k) => onFilterChange(k, ""))}
            >
              Clear All Filters
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
