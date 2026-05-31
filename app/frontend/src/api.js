const BASE = "";

export async function uploadGarment(file, metadata = {}) {
  const form = new FormData();
  form.append("file", file);
  for (const [k, v] of Object.entries(metadata)) {
    if (v) form.append(k, v);
  }
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

export async function fetchGarments(params = {}) {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v) qs.set(k, v);
  }
  const res = await fetch(`${BASE}/garments?${qs}`);
  if (!res.ok) throw new Error("Failed to fetch garments");
  return res.json();
}

export async function fetchGarment(id) {
  const res = await fetch(`${BASE}/garments/${id}`);
  if (!res.ok) throw new Error("Not found");
  return res.json();
}

export async function fetchFilters() {
  const res = await fetch(`${BASE}/filters`);
  if (!res.ok) throw new Error("Failed to fetch filters");
  return res.json();
}

export async function addAnnotation(garmentId, text, author = "user") {
  const res = await fetch(`${BASE}/garments/${garmentId}/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, author }),
  });
  if (!res.ok) throw new Error("Failed to add annotation");
  return res.json();
}

export async function deleteAnnotation(garmentId, index) {
  const res = await fetch(
    `${BASE}/garments/${garmentId}/annotations/${index}`,
    { method: "DELETE" }
  );
  if (!res.ok) throw new Error("Failed to delete annotation");
  return res.json();
}

export function imageUrl(filename) {
  return `${BASE}/images/${filename}`;
}
