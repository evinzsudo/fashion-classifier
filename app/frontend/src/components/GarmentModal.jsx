import { useState } from "react";
import { imageUrl, addAnnotation, deleteAnnotation } from "../api.js";

const ATTR_KEYS = [
  ["garment_type", "Type"],
  ["style", "Style"],
  ["material", "Material"],
  ["color_palette", "Color Palette"],
  ["pattern", "Pattern"],
  ["season", "Season"],
  ["occasion", "Occasion"],
  ["consumer_profile", "Consumer"],
  ["location_context", "Location"],
];

export default function GarmentModal({ garment: initial, onClose, onUpdate }) {
  const [garment, setGarment] = useState(initial);
  const [annotationText, setAnnotationText] = useState("");
  const [authorText, setAuthorText] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleAddAnnotation(e) {
    e.preventDefault();
    if (!annotationText.trim()) return;
    setSaving(true);
    try {
      const updated = await addAnnotation(
        garment.id,
        annotationText.trim(),
        authorText.trim() || "user"
      );
      setGarment(updated);
      onUpdate(updated);
      setAnnotationText("");
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteAnnotation(index) {
    const updated = await deleteAnnotation(garment.id, index);
    setGarment(updated);
    onUpdate(updated);
  }

  function formatDate(iso) {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2>{garment.garment_type || "Garment"}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <div className="modal-body">
          {/* Left: image */}
          <div className="modal-image-col">
            <img
              className="modal-image"
              src={imageUrl(garment.filename)}
              alt={garment.original_filename}
            />
            <div className="modal-filename">{garment.original_filename}</div>
            <div className="modal-filename" style={{ marginTop: 4 }}>
              Uploaded {formatDate(garment.upload_time)}
            </div>
          </div>

          {/* Right: details */}
          <div className="modal-details-col">
            {/* AI description */}
            <div>
              <div className="section-label">AI Description</div>
              <p className="description-text">{garment.raw_description}</p>
            </div>

            {/* Structured attributes */}
            <div>
              <div className="section-label">Attributes</div>
              <div className="attrs-grid">
                {ATTR_KEYS.map(([key, label]) => (
                  <div key={key} className="attr-row">
                    <span className="attr-key">{label}</span>
                    <span className={`attr-val${key === "trend_notes" ? " long" : ""}`}>
                      {garment[key] || "—"}
                    </span>
                  </div>
                ))}
                <div className="attr-row" style={{ gridColumn: "1/-1" }}>
                  <span className="attr-key">Trend Notes</span>
                  <span className="attr-val long">{garment.trend_notes || "—"}</span>
                </div>
              </div>
            </div>

            {/* Annotations — visually distinct amber section */}
            <div className="annotations-section">
              <div className="section-label">✏️ Annotations</div>

              {garment.annotations?.length === 0 && (
                <p className="annotation-empty">No annotations yet.</p>
              )}

              {garment.annotations?.map((ann, i) => (
                <div key={i} className="annotation-item">
                  <div className="annotation-content">
                    <div className="annotation-text">"{ann.text}"</div>
                    <div className="annotation-meta">
                      {ann.author} · {formatDate(ann.created_at)}
                    </div>
                  </div>
                  <button
                    className="annotation-delete-btn"
                    title="Delete annotation"
                    onClick={() => handleDeleteAnnotation(i)}
                  >
                    ×
                  </button>
                </div>
              ))}

              <form className="add-annotation-form" onSubmit={handleAddAnnotation}>
                <textarea
                  placeholder="Add a note, correction, or tag…"
                  value={annotationText}
                  onChange={(e) => setAnnotationText(e.target.value)}
                />
                <div className="annotation-form-row">
                  <input
                    type="text"
                    placeholder="Your name (optional)"
                    value={authorText}
                    onChange={(e) => setAuthorText(e.target.value)}
                  />
                  <button
                    type="submit"
                    className="save-annotation-btn"
                    disabled={!annotationText.trim() || saving}
                  >
                    {saving ? "Saving…" : "Save"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
