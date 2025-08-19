import React from 'react';
import { Link } from 'react-router-dom';
import './AdminFunctionNav.css';

export default function AdminFunctionNav() {
  return (
    <div className="admin-func-nav">
      <Link to="/app/user-management" className="nav-btn">User Management</Link>
      <Link to="/app/policy-management" className="nav-btn">Policy Management</Link>
      <Link to="/app/asset-management" className="nav-btn">Asset Management</Link>
      <Link to="/app/storage-management" className="nav-btn">Storage Management</Link>
    </div>
  );
}
