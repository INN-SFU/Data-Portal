import React, { useEffect, useState } from "react";
import axios from "axios";
import { useKeycloak } from "@react-keycloak/web";
import "./StorageManagement.css";

const http = axios.create({ baseURL: "http://localhost:8000" });
const INSTANCES_BASE = "/api/instances";
const FLAVOURS = ["s3", "posix"];

export default function StorageManagement() {
  const { keycloak, initialized } = useKeycloak();

  const [instances, setInstances] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  // form state
  const [instanceName, setInstanceName] = useState("my-instance-id");
  const [accessPointName, setAccessPointName] = useState("my-access-point");
  const [flavour, setFlavour] = useState("");
  // S3 fields
  const [s3Url, setS3Url] = useState("http://localhost:9000");
  const [s3Key, setS3Key] = useState("");
  const [s3Secret, setS3Secret] = useState("");
  // POSIX fields
  const [posixInstanceUrl, setPosixInstanceUrl] = useState("http://gateway.local:9000");
  const [posixRootPath, setPosixRootPath] = useState("/app/test-storage");
  const [posixIssuerUrl, setPosixIssuerUrl] = useState("http://issuer.local:8001");
  const [posixIssuerApiKey, setPosixIssuerApiKey] = useState("");
  const [posixInstanceUuid, setPosixInstanceUuid] = useState("");

  const authHeaders = async () => {
    if (!initialized) return {};
    try { await keycloak.updateToken(30); } catch {}
    return keycloak?.token ? { Authorization: `Bearer ${keycloak.token}` } : {};
  };

  async function loadInstances() {
    const headers = await authHeaders();
    const { data } = await http.get(`${INSTANCES_BASE}/`, { headers });
    setInstances(Array.isArray(data?.instances) ? data.instances : []);
  }

  useEffect(() => {
    (async () => {
      if (!initialized) return;
      try {
        await loadInstances();
      } catch (e) {
        setErr(toMsg(e));
      } finally {
        setLoading(false);
      }
    })();
  }, [initialized]);

  async function handleCreate(e) {
    e.preventDefault();
    setErr("");

    if (!instanceName.trim()) return setErr("Instance name is required.");
    if (!accessPointName.trim()) return setErr("Access point name is required.");
    if (!flavour) return setErr("Flavour is required.");

    let payload;
    if (flavour === "s3") {
      if (!s3Url.trim() || !s3Key.trim() || !s3Secret.trim()) {
        return setErr("For S3, please fill endpoint URL, access key, and secret.");
      }
      payload = {
        flavour: "s3",
        instance_name: instanceName.trim(),
        access_point_name: accessPointName.trim(),
        instance_url: s3Url.trim(),
        aws_access_key_id: s3Key.trim(),
        aws_secret_access_key: s3Secret.trim(),
      };
    } else if (flavour === "posix") {
      if (!posixInstanceUrl.trim() || !posixRootPath.trim() || !posixIssuerUrl.trim() ||
          !posixIssuerApiKey.trim() || !posixInstanceUuid.trim()) {
        return setErr("For POSIX, please fill all required fields.");
      }
      payload = {
        flavour: "posix",
        instance_name: instanceName.trim(),
        access_point_name: accessPointName.trim(),
        instance_url: posixInstanceUrl.trim(),
        root_path: posixRootPath.trim(),
        issuer_url: posixIssuerUrl.trim(),
        issuer_api_key: posixIssuerApiKey.trim(),
        instance_uuid: posixInstanceUuid.trim(),
      };
    } else {
      return setErr(`Unsupported flavour: ${flavour}`);
    }

    try {
      const headers = { ...(await authHeaders()) };
      await http.post(`${INSTANCES_BASE}/`, payload, { headers });
      await loadInstances();
      // light reset of sensitive fields
      setS3Key(""); setS3Secret(""); setPosixIssuerApiKey("");
      alert("Instance created.");
    } catch (e) {
      setErr(toMsg(e));
    }
  }

  async function handleDelete(i) {
    if (!window.confirm(`Delete instance "${i.name}" (${i.uuid})?`)) return;
    setErr("");
    try {
      const headers = await authHeaders();
      await http.delete(`${INSTANCES_BASE}/${encodeURIComponent(i.uuid)}`, { headers });
      setInstances(prev => prev.filter(x => x.uuid !== i.uuid));
    } catch (e) {
      setErr(toMsg(e));
    }
  }

  return (
    <div className="im-root">
      <h1>Storage Instances</h1>

      <section className="im-card">
        <h3>Create Instance</h3>
        <form onSubmit={handleCreate} className="im-form">
          <div className="im-row">
            <label className="im-field">
              <span>Instance Name *</span>
              <input value={instanceName} onChange={e => setInstanceName(e.target.value)} placeholder="my-instance-id" />
              <small className="im-muted">Used to derive a stable UUID</small>
            </label>
            <label className="im-field">
              <span>Access Point Name *</span>
              <input value={accessPointName} onChange={e => setAccessPointName(e.target.value)} placeholder="my-access-point" />
              <small className="im-muted">Human-friendly name shown in the UI</small>
            </label>
          </div>

          <label className="im-field">
            <span>Flavour *</span>
            <select value={flavour} onChange={e => setFlavour(e.target.value)}>
              <option value="">— Select flavour —</option>
              {FLAVOURS.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </label>

          {flavour === "s3" && (
            <div className="im-row">
              <label className="im-field">
                <span>S3 Endpoint URL *</span>
                <input value={s3Url} onChange={e => setS3Url(e.target.value)} placeholder="http://localhost:9000" />
              </label>
              <label className="im-field">
                <span>Access Key *</span>
                <input value={s3Key} onChange={e => setS3Key(e.target.value)} />
              </label>
              <label className="im-field">
                <span>Secret Key *</span>
                <input type="password" value={s3Secret} onChange={e => setS3Secret(e.target.value)} />
              </label>
            </div>
          )}

          {flavour === "posix" && (
            <>
              <div className="im-row">
                <label className="im-field">
                  <span>Gateway URL *</span>
                  <input value={posixInstanceUrl} onChange={e => setPosixInstanceUrl(e.target.value)} placeholder="http://gateway.local:9000" />
                  <small className="im-muted">Storage Gateway service URL for file downloads</small>
                </label>
                <label className="im-field">
                  <span>Root Path *</span>
                  <input value={posixRootPath} onChange={e => setPosixRootPath(e.target.value)} placeholder="/app/test-storage" />
                  <small className="im-muted">Absolute path to storage root directory</small>
                </label>
              </div>
              <div className="im-row">
                <label className="im-field">
                  <span>Issuer URL *</span>
                  <input value={posixIssuerUrl} onChange={e => setPosixIssuerUrl(e.target.value)} placeholder="http://issuer.local:8001" />
                  <small className="im-muted">Storage Issuer service URL for JWT generation</small>
                </label>
                <label className="im-field">
                  <span>Issuer API Key *</span>
                  <input type="password" value={posixIssuerApiKey} onChange={e => setPosixIssuerApiKey(e.target.value)} />
                  <small className="im-muted">API key for Issuer authentication</small>
                </label>
                <label className="im-field">
                  <span>Instance UUID *</span>
                  <input value={posixInstanceUuid} onChange={e => setPosixInstanceUuid(e.target.value)} placeholder="550e8400-e29b-41d4-a716-446655440000" />
                  <small className="im-muted">Instance UUID for policy tracking</small>
                </label>
              </div>
            </>
          )}

          <div className="im-actions">
            <button className="im-btn im-btn-primary" type="submit" disabled={!flavour}>Create</button>
            {err && <div className="im-error">{err}</div>}
          </div>
        </form>
      </section>

      <section className="im-grid">
        {loading ? (
          <div className="im-card"><p>Loading instances…</p></div>
        ) : instances.length === 0 ? (
          <div className="im-card"><p className="im-muted">No instances found.</p></div>
        ) : (
          instances.map(i => (
            <div key={i.uuid} className="im-card">
              <div className="im-head">
                <div className="im-title">
                  <strong>{i.name}</strong>
                  <span className="im-chip">{i.flavour}</span>
                </div>
                <div className="im-actions-right">
                  <button className="im-btn im-btn-danger" onClick={() => handleDelete(i)}>Delete</button>
                </div>
              </div>
              <div className="im-meta">
                <div><span className="im-key">UUID:</span> <code className="im-code">{i.uuid}</code></div>
                {i.config?.agent?.instance_url && (
                  <div><span className="im-key">Endpoint:</span> <code className="im-code">{i.config.agent.instance_url}</code></div>
                )}
              </div>
              {i.config && (
                <details className="im-details">
                  <summary>Config</summary>
                  <pre className="im-pre">{JSON.stringify(i.config, null, 2)}</pre>
                </details>
              )}
            </div>
          ))
        )}
      </section>
    </div>
  );
}

function toMsg(err) {
  const d = err?.response?.data;
  if (!d) return String(err?.message || err);
  if (Array.isArray(d.detail)) return d.detail.map(x => `${(x.loc || []).join(".")} → ${x.msg}`).join(" | ");
  return d.detail || JSON.stringify(d);
}
