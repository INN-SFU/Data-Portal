import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { useKeycloak } from '@react-keycloak/web';
import './PolicyManagement.css';

const http = axios.create({ baseURL: "http://localhost:8000" });

// flatten dict trees
function flattenTree(node, prefix = '') {
  // backend returns a dict of trees
  const out = [];
  const isArray = Array.isArray(node);
  const isObject = node && typeof node === 'object' && !isArray;

  if (isArray) {
    node.forEach(n => out.push(...flattenTree(n, prefix)));
    return out;
  }

  if (isObject) {
    const id = node.id || node.path || node.text || '';
    const here = id ? (id.startsWith('/') ? id : (prefix ? `${prefix}/${id}` : id)) : prefix;
    if (here) out.push(here);
    if (node.children) {
      node.children.forEach(c => out.push(...flattenTree(c, here)));
    }
    // If backend returned a plain dict { name: subtree }, flatten keys
    if (!node.id && !node.text && !node.children) {
      Object.entries(node).forEach(([k, v]) => {
        const here2 = prefix ? `${prefix}/${k}` : k;
        out.push(here2);
        out.push(...flattenTree(v, here2));
      });
    }
  }

  return out;
}

export default function PolicyManagement() {
  const { keycloak, initialized } = useKeycloak();

  const [policies, setPolicies] = useState([]);
  const [instances, setInstances] = useState([]);      
  const [assets, setAssets] = useState({});            
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  // form: create/delete
  const [username, setUsername] = useState('');
  const [instanceName, setInstanceName] = useState('');
  const [resource, setResource] = useState('');
  const [action, setAction] = useState('read');

  // auth header per call
  const authHeaders = async () => {
    if (!initialized) return {};
    try { await keycloak.updateToken(30); } catch {}
    return keycloak?.token ? { Authorization: `Bearer ${keycloak.token}` } : {};
  };

  // Load dashboard (instances, assets) + all policies
  async function loadDashboard() {
    const headers = await authHeaders();
    const { data } = await http.get('/api/policies/dashboard', { headers });
    setInstances(Array.isArray(data?.instances) ? data.instances : []);
    setAssets(data?.assets || {});
  }

  async function loadPolicies() {
    const headers = await authHeaders();
    const { data } = await http.get('/api/policies/', { headers });
    // backend returns { success, details }
    setPolicies(Array.isArray(data?.details) ? data.details : []);
  }

  useEffect(() => {
    (async () => {
      if (!initialized) return;
      try {
        await Promise.all([loadDashboard(), loadPolicies()]);
      } catch (e) {
        setErr(String(e.message || e));
      } finally {
        setLoading(false);
      }
    })();
  }, [initialized]);

  // resources list for selected instance
  const resourceHints = useMemo(() => {
    const tree = assets?.[instanceName];
    if (!tree) return [];
    const list = flattenTree(tree).filter(Boolean);
    return Array.from(new Set(list)).sort();
  }, [assets, instanceName]);

  // Create (POST with form-encoded fields)
  async function handleCreate(e) {
    e.preventDefault();
    setErr('');
    if (!username.trim()) return setErr('Username is required.');
    if (!instanceName.trim()) return setErr('Instance name is required.');
    if (!resource.trim()) return setErr('Resource is required.');
    if (!action.trim()) return setErr('Action is required.');

    try {
      const headers = await authHeaders();
      const form = new URLSearchParams({
        username: username.trim(),
        instance_name: instanceName.trim(),
        resource: resource.trim(),
        action: action.trim(),
      });
      await http.post('/api/policies/', form, {
        headers: { ...headers, 'Content-Type': 'application/x-www-form-urlencoded' }
      });
      await loadPolicies();
      setResource('');
      setAction('read');
      alert('Policy created.');
    } catch (e2) {
      setErr(String(e2.message || e2));
    }
  }

  // Delete (DELETE with query params)
  async function handleDelete(p) {

    if (!window.confirm(`Delete policy:\nresource="${p.resource}" action="${p.action}" ?`)) return;
    setErr('');
    try {
      const headers = await authHeaders();
 
      await http.delete('/api/policies/', {
        headers,
        params: {
          username,               
          instance_name: instanceName,
          resource: p.resource,
          action: p.action,
        }
      });
      await loadPolicies();
    } catch (e3) {
      setErr(String(e3.message || e3));
    }
  }

  // render helpers
  const instanceOptions = instances.map(i => i?.name).filter(Boolean);

  return (
    <div className="pm-root">
      <h1>Policy Management</h1>

      <section className="pm-card">
        <h3>Create Policy</h3>
        <form onSubmit={handleCreate} className="pm-form">
          <div className="pm-row">
            <label className="pm-field">
              <span>Username *</span>
              <input value={username} onChange={e => setUsername(e.target.value)} placeholder="alice" />
            </label>
            <label className="pm-field">
              <span>Instance *</span>
              <select value={instanceName} onChange={e => setInstanceName(e.target.value)}>
                <option value="">— Select —</option>
                {instanceOptions.map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </label>
          </div>

          <label className="pm-field">
            <span>Resource *</span>
            <input list="resource-hints" value={resource} onChange={e => setResource(e.target.value)} placeholder="/path/to/resource or folder" />
            {resourceHints.length > 0 && (
              <datalist id="resource-hints">
                {resourceHints.slice(0, 200).map(h => <option key={h} value={h} />)}
              </datalist>
            )}
          </label>

          <label className="pm-field">
            <span>Action *</span>
            <input value={action} onChange={e => setAction(e.target.value)} placeholder="read | write | delete | admin" />
          </label>

          <div className="pm-actions">
            <button className="pm-btn pm-btn-primary" type="submit">Create Policy</button>
            {err && <div className="pm-error">{err}</div>}
          </div>
        </form>
      </section>

      <section className="pm-card">
        <h3>Policies</h3>
        {loading ? (
          <p>Loading policies…</p>
        ) : (policies?.length ?? 0) === 0 ? (
          <p className="pm-muted">No policies found.</p>
        ) : (
          <table className="pm-table">
            <thead>
              <tr>
                <th>User UUID</th>
                <th>Instance UUID</th>
                <th>Resource</th>
                <th>Action</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {policies.map((p, idx) => (
                <tr key={idx}>
                  <td><code className="pm-mono">{String(p.user_uuid || '').slice(0, 12)}…</code></td>
                  <td><code className="pm-mono">{String(p.instance_uuid || '').slice(0, 12)}…</code></td>
                  <td>{p.resource || '—'}</td>
                  <td>{p.action || '—'}</td>
                  <td className="pm-actions-right">
                    <button className="pm-btn pm-btn-danger" onClick={() => handleDelete(p)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
