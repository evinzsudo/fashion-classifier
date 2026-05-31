import { useState, useEffect } from "react";
import { imageUrl, addAnnotation, deleteAnnotation, fetchSimilarGarments } from "../api.js";

const AI_ATTR_KEYS = [
  ["garment_type",      "Garment Type"],
  ["style",             "Style"],
  ["material",          "Material"],
  ["color_palette",     "Color Palette"],
  ["pattern",           "Pattern"],
  ["season",            "Season"],
  ["occasion",          "Occasion"],
  ["consumer_profile",  "Consumer Profile"],
  ["location_context",  "Location Context"],
];

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString(undefined, {
    hour: "2-digit", minute: "2-digit",
  });
}

function formatAnnotationDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export default function GarmentModal({ garment: initial, onClose, onUpdate, onNavigate }) {
  const [garment, setGarment] = useState(initial);
  const [annotationText, setAnnotationText] = useState("");
  const [authorText, setAuthorText] = useState("");
  const [saving, setSaving] = useState(false);
  const [similar, setSimilar] = useState([]);

  // Reload similar when the viewed garment changes
  useEffect(() => {
    setSimilar([]);
    fetchSimilarGarments(garment.id)
      .then(setSimilar)
      .catch(() => setSimilar([]));
  }, [garment.id]);

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

  function navigateTo(g) {
    setGarment(g);
    setAnnotationText("");
    setAuthorText("");
  }

  const confidence = garment.confidence || {};
  const isUncertain = (key) =>
    confidence[key] !== undefined && confidence[key] < 0.7;

  const locationParts = [garment.city, garment.country, garment.continent].filter(Boolean);

  return (
    <div
      className="modal-overlay"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="modal">
        {/* Blue header */}
        <div className="modal-header">
          <h2>Garment Details</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">×</button>
        </div>

        {/* Two-column body */}
        <div className="modal-body">
          {/* Left: image (60%) */}
          <div className="modal-image-col">
            <img
              className="modal-image"
              src={imageUrl(garment.filename)}
              alt={garment.garment_type || "Garment"}
            />
          </div>

          {/* Right: details (40%) */}
          <div className="modal-details-col">

            {/* Cache badge */}
            {garment.from_cache && (
              <div className="cache-badge">
                ⚡ Cached Result — served from library
              </div>
            )}

            {/* Description */}
            {garment.raw_description && (
              <div>
                <div className="section-label">Description</div>
                <p className="description-text">{garment.raw_description}</p>
              </div>
            )}

            {/* AI Attributes — 2-col grid with confidence styling */}
            <div>
              <div className="section-label">Attributes</div>
              <div className="attrs-grid">
                {AI_ATTR_KEYS.map(([key, label]) => (
                  <div key={key} className="attr-row">
                    <span className="attr-key">{label}</span>
                    <span className={`attr-val${isUncertain(key) ? " uncertain" : ""}`}>
                      {garment[key] || "—"}
                      {isUncertain(key) && (
                        <span className="confidence-hint" title={`Confidence: ${(confidence[key] * 100).toFixed(0)}%`}>
                          {" "}({(confidence[key] * 100).toFixed(0)}%)
                        </span>
                      )}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Trend Notes */}
            {garment.trend_notes && (
              <div>
                <div className="section-label">Trend Notes</div>
                <div className="trend-notes-box">{garment.trend_notes}</div>
              </div>
            )}

            {/* Annotations */}
            <div className="annotations-section">
              <div className="section-label">✏ Annotations</div>

              {garment.annotations?.length === 0 && (
                <p className="annotation-empty">No annotations yet.</p>
              )}

              {garment.annotations?.map((ann, i) => (
                <div key={i} className="annotation-item">
                  <div className="annotation-content">
                    <div className="annotation-text">"{ann.text}"</div>
                    <div className="annotation-meta">
                      {ann.author} · {formatAnnotationDate(ann.created_at)}
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

            {/* Context info box */}
            <div className="modal-context-box">
              <div className="section-label" style={{ marginBottom: 8 }}>Context</div>
              <div className="context-item">
                <span className="context-icon">📅</span>
                <span>{formatDate(garment.upload_time)} · {formatTime(garment.upload_time)}</span>
              </div>
              {garment.designer && (
                <div className="context-item">
                  <span className="context-icon">✂️</span>
                  <span>{garment.designer}</span>
                </div>
              )}
              {locationParts.length > 0 && (
                <div className="context-item">
                  <span className="context-icon">📍</span>
                  <span>{locationParts.join(", ")}</span>
                </div>
              )}
            </div>

            {/* Similar Garments */}
            {similar.length > 0 && (
              <div>
                <div className="section-label">Similar Garments</div>
                <div className="similar-row">
                  {similar.map((g) => (
                    <button
                      key={g.id}
                      className="similar-card"
                      onClick={() => navigateTo(g)}
                      title={g.garment_type || "Garment"}
                    >
                      <div className="similar-img-wrap">
                        <img
                          src={imageUrl(g.filename)}
                          alt={g.garment_type || "Garment"}
                          loading="lazy"
                        />
                      </div>
                      <div className="similar-label">{g.garment_type || "?"}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

          </div>
        </div>
      </div>
    </div>
  );
}
