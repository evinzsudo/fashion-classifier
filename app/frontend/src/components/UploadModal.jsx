import { useState, useEffect, useRef } from "react";

const CONTINENTS = [
  "Africa", "Asia", "Europe",
  "North America", "Oceania", "South America",
];

// Status icon for each queue item
function StatusIcon({ status }) {
  if (status === "done")      return <span className="queue-icon done">✓</span>;
  if (status === "failed")    return <span className="queue-icon failed">✗</span>;
  if (status === "uploading") return <span className="queue-spinner" />;
  return <span className="queue-icon waiting">○</span>;
}

export default function UploadModal({ files, onUploadFile, onComplete, onCancel }) {
  const [continent, setContinent] = useState("");
  const [country, setCountry]     = useState("");
  const [city, setCity]           = useState("");
  const [designer, setDesigner]   = useState("");

  const [phase, setPhase]       = useState("form"); // "form" | "processing"
  const [queue, setQueue]       = useState(() =>
    files.map((f) => ({ file: f, status: "waiting", error: null }))
  );
  const [currentIdx, setCurrentIdx] = useState(0);
  const [errorMsg, setErrorMsg]     = useState("");
  const processingRef = useRef(false);

  // Preview URL for first file
  const [previewUrl, setPreviewUrl] = useState(null);
  useEffect(() => {
    if (!files[0]) return;
    const url = URL.createObjectURL(files[0]);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [files]);

  async function handleSubmit(e) {
    e.preventDefault();
    if (processingRef.current) return;
    processingRef.current = true;
    setPhase("processing");
    setErrorMsg("");

    const metadata = { continent, country, city, designer };
    let succeeded = 0;
    let cachedCount = 0;
    const failedItems = [];

    for (let i = 0; i < files.length; i++) {
      setCurrentIdx(i);
      setQueue((q) =>
        q.map((item, idx) => (idx === i ? { ...item, status: "uploading" } : item))
      );
      try {
        const result = await onUploadFile(files[i], metadata);
        if (result?.from_cache) cachedCount++;
        succeeded++;
        setQueue((q) =>
          q.map((item, idx) => (idx === i ? { ...item, status: "done" } : item))
        );
      } catch (err) {
        const msg = err.message || "Upload failed";
        failedItems.push({ name: files[i].name, error: msg });
        setQueue((q) =>
          q.map((item, idx) =>
            idx === i ? { ...item, status: "failed", error: msg } : item
          )
        );
      }
    }

    processingRef.current = false;
    onComplete(succeeded, failedItems, cachedCount);
  }

  const isProcessing = phase === "processing";
  const doneCount  = queue.filter((q) => q.status === "done").length;
  const totalCount = files.length;

  return (
    <div
      className="modal-overlay"
      onClick={isProcessing ? undefined : (e) => e.target === e.currentTarget && onCancel()}
    >
      <div className="modal upload-modal">
        {/* Blue header */}
        <div className="modal-header">
          <h2>
            {isProcessing
              ? `Analyzing ${currentIdx + 1} of ${totalCount}…`
              : `Upload ${totalCount === 1 ? "Garment" : `${totalCount} Garments`}`}
          </h2>
          <button
            className="modal-close"
            onClick={isProcessing ? undefined : onCancel}
            disabled={isProcessing}
          >
            ×
          </button>
        </div>

        <div className="upload-modal-body">
          {/* Left: preview + file queue */}
          <div className="upload-preview-col">
            {files.length === 1 ? (
              <div className="upload-dnd-zone has-preview">
                {previewUrl && (
                  <img className="upload-preview-img" src={previewUrl} alt="Preview" />
                )}
              </div>
            ) : (
              <div className="upload-queue-list">
                {queue.map((item, i) => (
                  <div
                    key={i}
                    className={`queue-item${item.status === "uploading" ? " active" : ""}${item.status === "failed" ? " failed" : ""}`}
                  >
                    <StatusIcon status={item.status} />
                    <span className="queue-name" title={item.file.name}>
                      {item.file.name}
                    </span>
                    {item.error && (
                      <span className="queue-error" title={item.error}>!</span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {isProcessing && (
              <div className="upload-progress-bar-wrap" style={{ marginTop: 12 }}>
                <div
                  className="upload-progress-bar-fill"
                  style={{ width: `${totalCount > 0 ? (doneCount / totalCount) * 100 : 0}%` }}
                />
              </div>
            )}
          </div>

          {/* Right: metadata form or progress steps for single file */}
          {files.length === 1 && isProcessing ? (
            <div className="upload-classifying">
              <div className="upload-progress-bar-wrap">
                <div
                  className="upload-progress-bar-fill"
                  style={{
                    width: queue[0]?.status === "done" ? "100%"
                      : queue[0]?.status === "uploading" ? "55%"
                      : "0%",
                  }}
                />
              </div>
              <div className="upload-steps">
                {[
                  { label: "Uploading image…",   done: queue[0]?.status !== "waiting" },
                  { label: "Analyzing with AI…", done: queue[0]?.status === "done" },
                  { label: "Saving to library…", done: queue[0]?.status === "done" },
                ].map((step, i) => (
                  <div
                    key={i}
                    className={`upload-step${step.done ? " done" : ""}${!step.done && i === (queue[0]?.status === "uploading" ? 1 : 0) ? " active" : ""}`}
                  >
                    <span className="upload-step-icon">{step.done ? "✓" : ["⬆", "🔍", "💾"][i]}</span>
                    <span className="upload-step-label">{step.label}</span>
                    {!step.done && queue[0]?.status === "uploading" && i === 1 && (
                      <span className="upload-step-spinner" />
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <form className="upload-form-col" onSubmit={handleSubmit}>
              {errorMsg && (
                <div className="upload-error-banner">
                  {errorMsg}
                  <button
                    type="button"
                    className="upload-error-dismiss"
                    onClick={() => setErrorMsg("")}
                  >
                    ×
                  </button>
                </div>
              )}

              <p className="upload-form-hint">
                {files.length > 1
                  ? `${files.length} images queued. Metadata applies to all.`
                  : "All fields optional — stored as user-supplied metadata."}
              </p>

              <div className="upload-field-group">
                <label className="upload-field-label">Designer / Brand</label>
                <input
                  type="text"
                  className="upload-field-input"
                  placeholder="e.g. Acne Studios, Uniqlo…"
                  value={designer}
                  onChange={(e) => setDesigner(e.target.value)}
                  disabled={isProcessing}
                />
              </div>

              <div className="upload-field-group">
                <label className="upload-field-label">Continent</label>
                <select
                  className="upload-field-input"
                  value={continent}
                  onChange={(e) => setContinent(e.target.value)}
                  disabled={isProcessing}
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
                    disabled={isProcessing}
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
                    disabled={isProcessing}
                  />
                </div>
              </div>

              <div className="upload-form-actions">
                <button
                  type="button"
                  className="upload-cancel-btn"
                  onClick={onCancel}
                  disabled={isProcessing}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="upload-confirm-btn"
                  disabled={isProcessing}
                >
                  {files.length > 1 ? `Upload All (${files.length})` : "Classify & Save"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
