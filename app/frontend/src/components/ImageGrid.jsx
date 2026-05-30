import ImageCard from "./ImageCard.jsx";

export default function ImageGrid({ garments, loading, onCardClick }) {
  if (loading) {
    return (
      <div className="image-grid">
        <div className="loading-row">
          <span className="spinner-dark" />
          Loading…
        </div>
      </div>
    );
  }

  if (!garments.length) {
    return (
      <div className="empty-state">
        <h3>No garments found</h3>
        <p>Upload an image or adjust your filters.</p>
      </div>
    );
  }

  return (
    <div className="image-grid">
      {garments.map((g) => (
        <ImageCard key={g.id} garment={g} onClick={onCardClick} />
      ))}
    </div>
  );
}
