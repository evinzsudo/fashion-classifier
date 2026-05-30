import { imageUrl } from "../api.js";

export default function ImageCard({ garment, onClick }) {
  const annotationCount = garment.annotations?.length || 0;

  return (
    <div className="card" onClick={() => onClick(garment)}>
      <div className="card-img-wrap">
        {garment.filename ? (
          <img
            className="card-img"
            src={imageUrl(garment.filename)}
            alt={garment.original_filename}
            loading="lazy"
          />
        ) : (
          <div className="card-img-placeholder">🧥</div>
        )}
      </div>
      <div className="card-body">
        <div className="card-type">{garment.garment_type || "Unknown"}</div>
        <div className="card-tags">
          {garment.style && <span className="tag">{garment.style}</span>}
          {garment.season && <span className="tag">{garment.season}</span>}
          {garment.pattern && garment.pattern !== "solid" && (
            <span className="tag">{garment.pattern}</span>
          )}
        </div>
        {annotationCount > 0 && (
          <div className="card-annotation-badge">
            ✏️ {annotationCount} note{annotationCount !== 1 ? "s" : ""}
          </div>
        )}
      </div>
    </div>
  );
}
