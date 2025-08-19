import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useKeycloak } from '@react-keycloak/web';
import './StorageManagement.css';

const http = axios.create({ baseURL: "http://localhost:8000" });
const INSTANCES_BASE = '/api/instances';

export default function EndpointManagement() {
  const { keycloak, initialized } = useKeycloak();

  const [instances, setInstances] = useState([]);     // [{uuid,name,flavour,config}]
  const [flavours, setFlavours] = useState([]);       // array or object
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');
  const DEFAULT_FLAVOURS = ['s3', 'posix'];

  // form state (create)
  const [instanceName, setInstanceName] = useState('my-instance-id');      // used to derive stable UUID
  const [accessPointName, setAccessPointName] = useState('my-access-point'); // display/name
  const [flavour, setFlavour] = useState('');
  const [configText, setConfigText] = useState('');    // extra agent config JSON

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

  async function loadDashboard() {
    const headers = await authHeaders();
    const { data } = await http.get(`${INSTANCES_BASE}/dashboard`, { headers });
    setFlavours(data?.flavours ?? []);
  }

  useEffect(() => {
    (async () => {
      if (!initialized) return;
      try {
        await Promise.all([loadInstances(), loadDashboard()]);
      } catch (e) {
        setErr(String(e.message || e));
      } finally {
        setLoading(false);
      }
    })();
  }, [initialized]);

  // provide a template when flavour changes (only if config is empty)
  useEffect(() => {
    if (!flavour || configText.trim()) return;
    const lower = flavour.toLowerCase();
    if (lower.includes('s3') || lower.includes('minio')) {
      setConfigText(JSON.stringify({
        endpoint_url: "http://localhost:9000",
        bucket: "my-bucket",
        region: "us-east-1",
        access_key: "<key>",
        secret_key: "<secret>",
        secure: false
      }, null, 2));
    }
  }, [flavour]); 

  const flavourOptions = useMemo(() => {
    let backend = [];
    if (Array.isArray(flavours)) backend = flavours;
    else if (flavours && typeof flavours === 'object') backend = Object.keys(flavours);
  
    const all = [...DEFAULT_FLAVOURS, ...backend].map(String);
    const seen = new Set();
    return all.filter(f => {
      const k = f.toLowerCase();
      if (seen.has(k)) return false;
      seen.add(k);
      return true;
    });
  }, [flavours]);

  async function handleCreate(e) {
    e.preventDefault();
    setErr('');
  
    // basic form checks
    if (!instanceName.trim()) return setErr('Instance name is required.');
    if (!accessPointName.trim()) return setErr('Access point name is required.');
    if (!flavour.trim()) return setErr('Flavour is required.');
  
    // parse textarea JSON (can be empty -> {})
    let rawExtra = {};
    if (configText.trim()) {
      try {
        rawExtra = JSON.parse(configText);
      } catch {
        return setErr('Config JSON is invalid.');
      }
    }
  
    // normalize keys to what backend expects
    const extra = normalizeConfig(flavour, rawExtra);
  
    // client-side required-field check
    const missing = requiredKeysForFlavour(flavour).filter(k => !(k in extra));
    if (missing.length) {
      return setErr(`Missing required config for ${flavour}: ${missing.join(', ')}`);
    }
  
    const payload = {
      flavour,
      instance_name: instanceName.trim(),       
      access_point_name: accessPointName.trim(),// display/admin name
      ...extra,
    };
  
    try {
      const headers = await authHeaders();
      await http.post('/api/instances/', payload, { headers });
      await loadInstances();
      setConfigText(''); // clear config box
      alert('Instance created.');
    } catch (err) {
      setErr(explainFastApiError(err));
      // console for deeper debugging
    }
  }

  async function handleDelete(i) {
    if (!window.confirm(`Delete instance "${i.name}" (${i.uuid})?`)) return;
    setErr('');
    try {
      const headers = await authHeaders();
      await http.delete(`${INSTANCES_BASE}/${encodeURIComponent(i.uuid)}`, { headers });
      setInstances(prev => prev.filter(x => x.uuid !== i.uuid));
    } catch (e3) {
      setErr(String(e3.message || e3));
    }
  }

  return (
    <div className="im-root">
      <h1>Endpoint (Instance) Management</h1>

      <section className="im-card">
        <h3>Create Instance</h3>
        <form onSubmit={handleCreate} className="im-form">
          <div className="im-row">
            <label className="im-field">
              <span>Instance Name *</span>
              <input value={instanceName} onChange={e => setInstanceName(e.target.value)} placeholder="my-instance-id" />
              <small className="im-muted">Internal ID used to derive a stable UUID (don’t change after creation)</small>
            </label>
            <label className="im-field">
              <span>Access Point Name *</span>
              <input value={accessPointName} onChange={e => setAccessPointName(e.target.value)} placeholder="my-access-point" />
              <small className="im-muted">Displayed name for this connection instance in the dashboard</small>
            </label>
          </div>

          <label className="im-field">
            <span>Flavour *</span>
            <select value={flavour} onChange={e => setFlavour(e.target.value)}>
              <option value="">— Select flavour —</option>
              {flavourOptions.map(f => <option key={f} value={f}>{f}</option>)}
            </select>
          </label>

          <label className="im-field">
            <span>Agent Config (JSON)</span>
            <textarea rows={7} value={configText} onChange={e => setConfigText(e.target.value)}
              placeholder='{"endpoint_url":"http://localhost:9000","bucket":"my-bucket","region":"us-east-1","access_key":"...","secret_key":"...","secure":false}' />
          </label>

          <div className="im-actions">
            <button className="im-btn im-btn-primary" type="submit">Create</button>
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
          instances.map((i) => (
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

///////////////////////////////////////////
// ---- helpers ----
function explainFastApiError(err) {
  const d = err?.response?.data;
  if (!d) return String(err?.message || err);
  if (Array.isArray(d.detail)) {
    return d.detail.map(x => `${(x.loc || []).join('.')} → ${x.msg}`).join(' | ');
  }
  return d.detail || JSON.stringify(d);
}

function normalizeConfig(flavour, cfg) {
  const f = (flavour || '').toLowerCase();

  // Map common aliases to backend keys
  if (f === 's3' || f === 'minio') {
    return {
      // backend expects these exact names
      instance_url:          cfg.instance_url          ?? cfg.endpoint_url,
      bucket_name:           cfg.bucket_name           ?? cfg.bucket,
      region_name:           cfg.region_name           ?? cfg.region,
      aws_access_key_id:     cfg.aws_access_key_id     ?? cfg.access_key,
      aws_secret_access_key: cfg.aws_secret_access_key ?? cfg.secret_key,
      secure: typeof cfg.secure === 'string'
        ? ['true', '1', 'yes'].includes(cfg.secure.toLowerCase())
        : Boolean(cfg.secure),
    };
  }

  if (f === 'posix') {
    return {
      instance_url: cfg.instance_url ?? cfg.url, 
      ssh_ca_key:   cfg.ssh_ca_key   ?? cfg.ca_key,

    };
  }

  return cfg;
}

function requiredKeysForFlavour(flavour) {
  const f = (flavour || '').toLowerCase();
  if (f === 's3' || f === 'minio') {
    return ['instance_url', 'bucket_name', 'region_name', 'aws_access_key_id', 'aws_secret_access_key', 'secure'];
  }
  if (f === 'posix') {
    return ['instance_url', 'ssh_ca_key'];
  }
  return [];
}