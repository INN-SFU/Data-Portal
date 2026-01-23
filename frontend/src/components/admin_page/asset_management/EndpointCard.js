import React, { useState } from "react";
import Tree from "./Tree.js";
import { CircularProgress } from "@mui/material";

export default function EndpointCard({
  endpointName,
  endpointUuid,
  treesByAccess,          // { read: jsTree[], write: jsTree[] } or jsTree[]
  selectedByAccess,       // { read: Set<string>, write: Set<string> }
  onSelectedChange,       // (access: 'read'|'write', nextSet: Set<string>) => void
  authHeaders,
  http,
  onMutate,               // call after upload to refresh parent
  busy,
  setBusy,
  busyID,
  setBusyID,
}) {
  const [open, setOpen] = useState(true);

  // Normalize to explicit read/write arrays
  const access = normalizeAccess(treesByAccess);
  const readArray = access.read;
  const writeArray = access.write;
  const deleteArray = access.delete;
  const hasRead = readArray.length > 0;
  const hasWrite = writeArray.length > 0;
  const hasDelete = deleteArray.length > 0;

  // Compute selections we need
  const readLeaves = getSelectedLeaves(readArray, selectedByAccess.read || new Set());
  const writeTopFolders = getSelectedTopFolders(writeArray, selectedByAccess.write || new Set());
  const deleteLeaves = getSelectedLeaves(deleteArray, selectedByAccess.write || new Set());

  const onTreeChange = (accessKey) => (nextSet) =>
    onSelectedChange(accessKey, new Set(nextSet));

  // --------------------- Download (from READ selection) ---------------------
  const handleDownload = async () => {
    if (!hasRead) return alert("No read permission.");
    if (readLeaves.length === 0) return alert("Select files/folders in READ.");

    setBusy("down");
    setBusyID(endpointUuid)
    try {
      const [{ default: JSZip }, { saveAs }] = await Promise.all([
        import("jszip"),
        import("file-saver"),
      ]);
      const zip = new JSZip();

      for (const id of readLeaves) {
        const headers = await authHeaders();
        const params = { instance_name: endpointName, resource: String(id), action: "read" };
        const { data } = await http.get("/assets/download", { params, headers });
        const urls = data?.presigned_urls || [];
        const paths = data?.file_paths || [];
        for (let i = 0; i < urls.length; i++) {
          const resp = await fetch(urls[i], { method: "GET", credentials: "omit", cache: "no-store" });
          if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
          zip.file(paths[i] || `file_${i}`, await resp.blob());
        }
      }

      const blob = await zip.generateAsync({ type: "blob" });
      saveAs(blob, `${endpointName}_download.zip`);
      console.log(`[Download] Successfully downloaded ${readLeaves.length} file(s) from endpoint "${endpointName}"`);
    } catch (e) {
      console.error(`[Download] Download failed for endpoint "${endpointName}":`, e);
      alert(`Download failed!`);
    } finally {
      setBusy(null);
      setBusyID(null);
    }
  };

  // ---------------------- Upload (to WRITE selection) ----------------------
  const handleUpload = async () => {
    if (!hasWrite) {
      return alert("Upload failed: You do not have write permission for this endpoint");
    }
    if (writeTopFolders.length === 0) {
      return alert("Upload failed: You do not have write access to this folder");
    }
    if (writeTopFolders.length > 1) {
      return alert("Upload failed: Please select exactly ONE folder to upload to");
    }

    const destDir = String(writeTopFolders[0]);

    const input = document.createElement("input");
    input.type = "file";
    input.multiple = true;
    input.style.position = "fixed";
    input.style.left = "-9999px";
    document.body.appendChild(input);

    input.onchange = async () => {
      if (!input.files || input.files.length === 0) {
        document.body.removeChild(input);
        return;
      }
      setBusy("up");
      setBusyID(endpointUuid)
      try {
        for (const file of Array.from(input.files)) {
          const resource = joinPath(destDir, file.name);
          const headers = await authHeaders();

          // Ask backend for presigned URL(s)
          const { data } = await http.put("/assets/upload", null, {
            params: { instance_name: endpointName, resource },
            headers,
          });

          const list = normalizePresigns(data?.presigned_urls ?? data?.urls ?? data?.url);
          for (const entry of list) {
            await uploadViaPresigned(entry, file);
          }
        }
        if (onMutate) onMutate(); // refresh dashboard with ?refresh=1 upstream  ------> TODO: need to further investigate refresh dashboard after upload or cerated new policy
        console.log(`[Upload] Successfully uploaded ${input.files.length} file(s) to "${destDir}" in endpoint "${endpointName}"`);
        alert("Upload complete.");
      } catch (e) {
        console.error(`[Upload] Upload failed for endpoint "${endpointName}" to destination "${destDir}":`, e);
        alert(`Upload failed!`);
      } finally {
        setBusy(null);
        setBusyID(null);
        try { document.body.removeChild(input); } catch {}
      }
    };

    input.click();
  };

  // ---------------------- Delete (from DELETE selection) ----------------------
  const handleDelete = async () => {
    if (!hasDelete) return alert("No delete permission.");
    if (deleteLeaves.length === 0) return alert("Select files to delete.");

    if (!window.confirm(`Delete ${deleteLeaves.length} file(s)? This cannot be undone.`)) return;

    setBusy("del");
    setBusyID(endpointUuid)
    try {
      for (const resource of deleteLeaves) {
        const headers = await authHeaders();

        // Ask backend for presigned DELETE URL
        const { data } = await http.delete("/assets/delete", {
          params: { instance_name: endpointName, resource },
          headers,
        });

        const urls = data?.presigned_urls || [];
        for (const url of urls) {
          const resp = await fetch(url, { method: "DELETE", credentials: "omit", cache: "no-store", mode: "cors" });
          if (!resp.ok) throw new Error(`Storage DELETE failed (${resp.status}): ${await safeText(resp)}`);
        }
      }
      console.log(`[Delete] Successfully deleted ${deleteLeaves.length} file(s) from endpoint "${endpointName}"`);
      if (onMutate) onMutate(); // refresh dashboard
      alert("Delete complete.");
    } catch (e) {
      console.error(`[Delete] Delete failed for endpoint "${endpointName}" while attempting to delete ${deleteLeaves.length} file(s):`, e);
      alert(`Delete failed!`);
    } finally {
      setBusy(null);
      setBusyID(null);
    }
  };

  // ------------------------------- HTML  --------------------------------
  return (
    <div
      style={{
        border: "1px solid #e5e7eb",
        borderRadius: 12,
        overflow: "hidden",
      }}
    >
      <div
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: 12,
          cursor: "pointer",
          background: "#f9fafb",
        }}
      >
        <div>
          <strong>{endpointName}</strong>
          <div style={{ fontSize: 12, color: "#6b7280" }}>
            UUID: {endpointUuid}
          </div>
        </div>
        <div style={{ fontSize: 14, color: "#6b7280" }}>{open ? "▼" : "▶"}</div>
      </div>

      {open && (
        <div style={{ padding: 12 }}>
          {!hasRead && !hasWrite  && !hasDelete ? (
            <div style={{ color: "#6b7280" }}>No tree data.</div>
          ) : (
            <div style={{ display: "grid", gap: 16 }}>
              {hasRead && (
                <div>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 6,
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>Read</div>
                    <button
                      onClick={handleDownload}
                      disabled={!!busy}
                      style={{
                        background: busy ? "#9ca3af" : "#3b82f6",
                        cursor: busy ? "not-allowed" : "pointer",
                        color: "#fff",
                        border: 0,
                        borderRadius: 8,
                        padding: "6px 10px",
                        fontSize: 13,
                        display: "flex",
                        alignItems: "center",
                        gap: 6,
                      }}
                    >
                      {busy === "down" && busyID == endpointUuid && (<CircularProgress size={14} sx={{ color: "#fff" }} />)}
                      {busy === "down" && busyID == endpointUuid ? "Downloading…" : "Download"}
                    </button>
                  </div>
                  <Tree
                    nodes={readArray}
                    selected={selectedByAccess.read || new Set()}
                    onChange={onTreeChange("read")}
                  />
                </div>
              )}
              {(hasWrite || hasDelete) && (
                <div
                  style={{
                    borderTop: hasRead ? "1px dashed #e5e7eb" : "none",
                    paddingTop: hasRead ? 8 : 0,
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 6,
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>Write</div>
                    <div style={{ display: "flex", gap: 8 }}>
                      <button
                        onClick={handleUpload}
                        disabled={!!busy}
                        style={{
                          background: busy ? "#9ca3af" : "#10b981",
                          cursor: busy ? "not-allowed" : "pointer",
                          color: "#fff",
                          border: 0,
                          borderRadius: 8,
                          padding: "6px 10px",
                          fontSize: 13,
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        {busy === "up" && busyID == endpointUuid && (<CircularProgress size={14} sx={{ color: "#fff" }} />)}
                        {busy === "up" && busyID == endpointUuid ? "Uploading…" : "Upload"}
                      </button>
                      <button
                        onClick={handleDelete}
                        disabled={!!busy}
                        style={{
                          background: busy ? "#9ca3af": "#ef4444",
                          cursor: busy ? "not-allowed" : "pointer",
                          color: "#fff",
                          border: 0,
                          borderRadius: 8,
                          padding: "6px 10px",
                          fontSize: 13,
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        {busy === "del" && busyID == endpointUuid && (<CircularProgress size={14} sx={{ color: "#fff" }} />)}
                        {busy === "del" && busyID == endpointUuid ? "Deleting…" : "Delete"}
                      </button>
                    </div>
                  </div>
                  <Tree
                    nodes={mergeTreeArrays(writeArray, deleteArray)}
                    selected={selectedByAccess.write || new Set()}
                    onChange={onTreeChange("write")}
                  />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------------- helpers ---------------- */

function normalizeAccess(input) {
  if (!input) return { read: [], write: [], delete: [] };
  if (Array.isArray(input)) return { read: input, write: [], delete: [] };
  if (typeof input === "object") {
    return {
      read: Array.isArray(input.read) ? input.read : [],
      write: Array.isArray(input.write) ? input.write : [],
      delete: Array.isArray(input.delete) ? input.delete : [],
    };
  }
  return { read: [], write: [], delete: [] };
}

// selected leaf files for READ (ids that are not any node's parent)
function getSelectedLeaves(list, sel) {
  const parents = new Set(list.filter(n => n.parent !== "#").map(n => String(n.parent)));
  const ids = new Set(list.map(n => String(n.id)));
  const out = [];
  sel.forEach((id) => {
    const s = String(id);
    if (ids.has(s) && !parents.has(s)) out.push(s);
  });
  return out;
}

// selected top-most folders for WRITE
function getSelectedTopFolders(list, sel) {
  const parentOf = new Map(list.map(n => [String(n.id), String(n.parent)]));
  const parentIds = new Set(list.filter(n => n.parent !== "#").map(n => String(n.parent)));

  // Include both folders with children AND top-level buckets (parent === "#")
  const chosenFolders = Array.from(sel).map(String).filter(id => {
    const node = list.find(n => String(n.id) === id);
    return node && (parentIds.has(id) || node.parent === "#");
  });

  const chosenSet = new Set(chosenFolders);
  return chosenFolders.filter(id => !chosenSet.has(parentOf.get(id)));
}

function joinPath(dir, name) {
  if (!dir) return name;
  return dir.endsWith("/") ? dir + name : `${dir}/${name}`;
}

// --- presigned upload helpers ---

function isSigV2(url) {
  try {
    const u = new URL(url);
    return u.searchParams.has("AWSAccessKeyId") && u.searchParams.has("Signature") && u.searchParams.has("Expires");
  } catch { return false; }
}

async function readFileAsArrayBuffer(file) {
  if (typeof file?.arrayBuffer === "function") return await file.arrayBuffer();
  return await new Promise((res, rej) => {
    const r = new FileReader();
    r.onerror = () => rej(r.error || new Error("FileReader error"));
    r.onload = () => res(r.result);
    r.readAsArrayBuffer(file);
  });
}

async function uploadViaPresigned(entry, file) {
  if (typeof entry === "string") {
    if (isSigV2(entry)) {
      const buf = await readFileAsArrayBuffer(file);
      const r = await fetch(entry, { method: "PUT", body: buf, credentials: "omit", cache: "no-store", mode: "cors" });
      if (!r.ok) throw new Error(`Storage PUT failed (${r.status}): ${await safeText(r)}`);
      return;
    }
    let r = await fetch(entry, { method: "PUT", body: file, credentials: "omit", cache: "no-store", mode: "cors" });
    if (r.ok) return;
    r = await fetch(entry, { method: "PUT", headers: { "Content-Type": "application/octet-stream" }, body: file, credentials: "omit", cache: "no-store", mode: "cors" });
    if (r.ok) return;
    if (file.type) {
      r = await fetch(entry, { method: "PUT", headers: { "Content-Type": file.type }, body: file, credentials: "omit", cache: "no-store", mode: "cors" });
      if (r.ok) return;
    }
    throw new Error(`Storage PUT failed (${r.status}): ${await safeText(r)}`);
  }

  if (entry && typeof entry === "object") {
    const url = entry.url || entry.href;
    if (!url) throw new Error("Presigned entry missing url.");
    if (entry.fields && typeof entry.fields === "object") {
      const fd = new FormData();
      for (const [k, v] of Object.entries(entry.fields)) fd.append(k, v);
      fd.append("file", file);
      const r = await fetch(url, { method: "POST", body: fd, credentials: "omit", cache: "no-store", mode: "cors" });
      if (!r.ok) throw new Error(`Storage POST failed (${r.status}): ${await safeText(r)}`);
      return;
    }
    const method = (entry.method || "PUT").toUpperCase();
    const headers = entry.headers || undefined;
    const r = await fetch(url, { method, headers, body: file, credentials: "omit", cache: "no-store", mode: "cors" });
    if (!r.ok) throw new Error(`Storage ${method} failed (${r.status}): ${await safeText(r)}`);
    return;
  }

  throw new Error("Unknown presigned URL format.");
}
//Return response text; if reading fails, return empty string
async function safeText(res) {
  try { return await res.text(); } catch { return ""; }
}

// cehck if presigned URLs are always from an array ([], [p], or p if already array)
function normalizePresigns(p) {
  return Array.isArray(p) ? p : (p ? [p] : []);
}

// Merge two tree arrays into a unique set of nodes by id
function mergeTreeArrays(arr1, arr2) {
  const map = new Map(arr1.map(node => [node.id, node]));

  // Add unique elements of second array
  for (const node of arr2) {
    if (!map.has(node.id)) {
      map.set(node.id, node);
    }
  }

  return Array.from(map.values());
}
