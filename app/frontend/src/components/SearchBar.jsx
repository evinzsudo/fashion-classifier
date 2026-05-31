import { useState, useEffect, useRef, forwardRef } from "react";

const SearchBar = forwardRef(function SearchBar({ value, onChange }, ref) {
  return (
    <div className="search-bar">
      <svg
        width="16" height="16" viewBox="0 0 15 15" fill="none"
        style={{ flexShrink: 0, color: "var(--text-muted)" }}
        aria-hidden="true"
      >
        <path
          d="M10 6.5a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Zm-.7 3.507 2.846 2.847a.5.5 0 0 1-.707.707L8.593 9.814A4.5 4.5 0 1 1 9.3 10.007Z"
          fill="currentColor"
        />
      </svg>
      <input
        ref={ref}
        type="text"
        placeholder="Search garments, descriptions, annotations..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-label="Search garments"
      />
      {value && (
        <button className="search-clear" onClick={() => onChange("")} aria-label="Clear search">
          ×
        </button>
      )}
      {!value && (
        <span className="search-hint" aria-hidden="true">/</span>
      )}
    </div>
  );
});

export default SearchBar;
