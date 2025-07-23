import React from "react";
import { BrowserRouter as Router } from "react-router-dom";
import { ReactKeycloakProvider } from "@react-keycloak/web";
import keycloak from "./setting/Keycloak";
import AppRouter from "./router/AppRouter";

function App() {
  return (
    <ReactKeycloakProvider
      authClient={keycloak}
      initOptions={{
        onLoad: "check-sso",
        silentCheckSsoRedirectUri: `${window.location.origin}/silent-check-sso.html`,
      }}
    >
      <Router>
        <AppRouter />
      </Router>
    </ReactKeycloakProvider>
  );
}

export default App;


