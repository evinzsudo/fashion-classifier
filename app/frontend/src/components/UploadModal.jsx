import { useState, useEffect, useRef } from "react";

const CONTINENTS = [
  "Africa", "Asia", "Europe",
  "North America", "Oceania", "South America",
];

const STEPS = [
  { label: "Uploading image…",       icon: "⬆" },
  { label: "Analyzing with AI…",     icon: "🔍" },
  { label: "Saving to library…",     icon: "💾" },
];

const STEP_DELAYS = [1500, 7000];

const PROGRESS_PER_STEP = [15, 55, 90];

export default function UploadModal({ file, onConfirm, onCancel }) {
  const [previewUrl, setPreviewUrl] = useState(null);
  const [continent, setContinent] = useState("");
  const [country, setCountry] = useState("");
  const [city, setCity] = useState("");
  const [designer, setDesigner] = useState("");
  const [status, setStatus] = useState("idle");
  const [errorMsg, setErrorMsg] = useState("");
  const [stepIdx, setStepIdx] = useState(0);
  const stepTimers = useRef([]);

  useEffect(() => {
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => {
    stepTimers.current.forEach(clearTimeout);
    stepTimers.current = [];
    if (status !== "loading") {
      setStepIdx(0);
      return;
    }
    STEP_DELAYS.forEach((delay, i) => {
      stepTimers.current.push(
        setTimeout(() => setStepIdx(i + 1), delay)
      );
    });
    return () => stepTimers.current.forEach(clearTimeout);
  }, [status]);

  const isLoading = status === "loading";
  const progressWidth = isLoading ? PROGRESS_PER_STEP[stepIdx] ?? 90 : 0;

  async function handleSubmit(e) {
    e.preventDefault();
    if (isLoading) return;
    setStatus("loading");
    setErrorMsg("");
    try {
      await onConfirm({ continent, country, city, designer });
    } catch (err) {
      setStatus("error");
      setErrorMsg(err.message || "Classification failed. Please try again.");
    }
  }

  return (
    <div
      className="modal-overlay"
      onClick={isLoading ? undefined : (e) => e.target === e.currentTarget && onCancel()}
    >
      <div className="modal upload-modal">
        {/* Blue header */}
        <div className="modal-header">
          <h2>Upload Garment</h2>
          <button
            className="modal-close"
            onClick={isLoading ? undefined : onCancel}
            disabled={isLoading}
          >
            ×
          </button>
        </div>

        <div className="upload-modal-body">
          {/* Preview column */}
          <div className="upload-preview-col">
            <div className={`upload-dnd-zone${previewUrl ? " has-preview" : ""}`}>
              {previewUrl ? (
                <img className="upload-preview-img" src={previewUrl} alt="Preview" />
              ) : (
                <>
                  <div className="upload-dnd-icon">📷</div>
                  <div className="upload-dnd-text">Image preview</div>
                </>
              )}
            </div>
            {file && (
              <div className="upload-preview-name">{file.name}</div>
            )}
          </div>

          {/* Right column */}
          {isLoading ? (
            <div className="upload-classifying">
              {/* Animated progress bar */}
              <div className="upload-progress-bar-wrap">
                <div
                  className="upload-progress-bar-fill"
                  style={{ width: `${progressWidth}%` }}
                />
              </div>

              <div className="upload-steps">
                {STEPS.map((step, i) => (
                  <div
                    key={i}
                    className={`upload-step${i < stepIdx ? " done" : ""}${i === stepIdx ? " active" : ""}`}
                  >
                    <span className="upload-step-icon">
                      {i < stepIdx ? "✓" : step.icon}
                    </span>
                    <span className="upload-step-label">{step.label}</span>
                    {i === stepIdx && (
                      <span className="upload-step-spinner" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <form className="upload-form-col" onSubmit={handleSubmit}>
              {status === "error" && (
                <div className="upload-error-banner">
                  {errorMsg}
                  <button
                    type="button"
                    className="upload-error-dismiss"
                    onClick={() => setStatus("idle")}
                  >
                    ×
                  </button>
                </div>
              )}

              <p className="upload-form-hint">
                All fields optional — stored as user-supplied metadata, not AI-inferred.
              </p>

              <div className="upload-field-group">
                <label className="upload-field-label">Designer / Brand</label>
                <input
                  type="text"
                  className="upload-field-input"
                  placeholder="e.g. Acne Studios, Uniqlo…"
                  value={designer}
                  onChange={(e) => setDesigner(e.target.value)}
                />
              </div>

              <div className="upload-field-group">
                <label className="upload-field-label">Continent</label>
                <select
                  className="upload-field-input"
                  value={continent}
                  onChange={(e) => setContinent(e.target.value)}
                >
                  <option value="">— Select —</option>
                  {CONTINENTS.map((c) => (
                    <option key={c} value={c}>{c}</option>
                  ))}
                </select>
              </div>

              <div className="upload-field-row">
                <div className="upload-field-group">
                  <label className="upload-field-label">Country</label>
                  <input
                    type="text"
                    className="upload-field-input"
                    placeholder="e.g. Japan"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                  />
                </div>
                <div className="upload-field-group">
                  <label className="upload-field-label">City</label>
                  <input
                    type="text"
                    className="upload-field-input"
                    placeholder="e.g. Tokyo"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                  />
                </div>
              </div>

              <div className="upload-form-actions">
                <button type="button" className="upload-cancel-btn" onClick={onCancel}>
                  Cancel
                </button>
                <button type="submit" className="upload-confirm-btn">
                  Classify &amp; Save
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
