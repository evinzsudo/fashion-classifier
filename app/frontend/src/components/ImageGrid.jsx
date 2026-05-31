import ImageCard from "./ImageCard.jsx";

const SKELETON_COUNT = 8;

function SkeletonCard() {
  return (
    <div className="card" aria-hidden="true">
      <div className="skeleton skeleton-img-block" />
      <div className="card-body">
        <div className="skeleton skeleton-line" style={{ width: "55%", height: 14 }} />
        <div className="skeleton skeleton-line" style={{ width: "38%", height: 10, marginTop: 8, borderRadius: 3 }} />
        <div className="skeleton skeleton-line" style={{ width: "28%", height: 10, marginTop: 4, borderRadius: 3 }} />
      </div>
    </div>
  );
}

function EmptyState({ hasFilters, searchTerm, onClearFilters }) {
  const heading = searchTerm
    ? `No results for "${searchTerm}"`
    : hasFilters
    ? "No garments match your filters"
    : "No garments yet";

  return (
    <div className="empty-state">
      <div className="empty-icon">🧥</div>
      <h3>{heading}</h3>
      {hasFilters || searchTerm ? (
        <p>
          Try a different search or{" "}
          <button className="empty-clear-link" onClick={onClearFilters}>
            clear all filters
          </button>
          .
        </p>
      ) : (
        <>
          <p>Upload a garment photo to get started.</p>
          <p className="empty-sub">
            No garments yet — upload your first inspiration image
          </p>
        </>
      )}
    </div>
  );
}

export default function ImageGrid({
  garments,
  loading,
  onCardClick,
  searchTerm,
  hasFilters,
  onClearFilters,
}) {
  if (loading) {
    return (
      <div className="image-grid">
        {Array.from({ length: SKELETON_COUNT }, (_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (!garments.length) {
    return (
      <div className="image-grid">
        <EmptyState
          hasFilters={hasFilters}
          searchTerm={searchTerm}
          onClearFilters={onClearFilters}
        />
      </div>
    );
  }

  return (
    <div className="image-grid">
      {garments.map((g) => (
        <ImageCard
          key={g.id}
          garment={g}
          onClick={onCardClick}
          searchTerm={searchTerm}
        />
      ))}
    </div>
  );
}
