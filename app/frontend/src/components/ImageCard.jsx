import { imageUrl } from "../api.js";

function highlight(text, term) {
  if (!term || !text) return text;
  const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = text.split(new RegExp(`(${escaped})`, "gi"));
  if (parts.length === 1) return text;
  return parts.map((part, i) =>
    i % 2 === 1
      ? <mark key={i} className="search-highlight">{part}</mark>
      : part
  );
}

export default function ImageCard({ garment, onClick, searchTerm }) {
  const annotationCount = garment.annotations?.length || 0;

  return (
    <div className="card" onClick={() => onClick(garment)}>
      <div className="card-img-wrap">
        {garment.filename ? (
          <img
            className="card-img"
            src={imageUrl(garment.filename)}
            alt={garment.garment_type || "Garment"}
            loading="lazy"
          />
        ) : (
          <div className="card-img-placeholder">🧥</div>
        )}

        {/* Annotation badge — top-right corner */}
        {annotationCount > 0 && (
          <div className="card-annotation-corner">
            ✏ {annotationCount}
          </div>
        )}

        {/* Hover overlay: quick attribute preview */}
        <div className="card-hover-overlay">
          {garment.style && (
            <div className="hover-attr">
              <span className="hover-attr-key">Style</span>
              <span className="hover-attr-val">{garment.style}</span>
            </div>
          )}
          {garment.material && (
            <div className="hover-attr">
              <span className="hover-attr-key">Material</span>
              <span className="hover-attr-val">{garment.material}</span>
            </div>
          )}
          {garment.occasion && (
            <div className="hover-attr">
              <span className="hover-attr-key">Occasion</span>
              <span className="hover-attr-val">{garment.occasion}</span>
            </div>
          )}
          {garment.color_palette && (
            <div className="hover-attr">
              <span className="hover-attr-key">Color</span>
              <span className="hover-attr-val">{garment.color_palette}</span>
            </div>
          )}
        </div>
      </div>

      <div className="card-body">
        <div className="card-type">{garment.garment_type || "Unknown"}</div>
        <div className="card-chips">
          {garment.style && <span className="chip">{garment.style}</span>}
          {garment.season && <span className="chip">{garment.season}</span>}
        </div>
      </div>
    </div>
  );
}
