import React from "react";
import PersonIcon from '@mui/icons-material/Person';
import keycloak from "../../setting/Keycloak";
import "./Navbar.css";

function Navbar() {
  const isLoggedIn = keycloak.authenticated;

  return (
    <nav className="navbar">
      <div className="navbar-left">INN Data Portal</div>
      <div className="navbar-right">
        <a href="/" className="navbar-link">Home</a>
        <a href="/about" className="navbar-link">About</a>
        {isLoggedIn && (
          <div className="navbar-user">
            <span>{keycloak.tokenParsed?.preferred_username}</span>
            <PersonIcon />
          </div>
        )}
        <button
          className={`navbar-button ${isLoggedIn ? "logout" : ""}`}
          onClick={() =>
            isLoggedIn
              ? keycloak.logout()
              : keycloak.login({ redirectUri: window.location.origin + "/app" })
          }
        >
          {isLoggedIn ? "Logout" : "Login"}
        </button>
      </div>
    </nav>
  );
}

export default Navbar;
