import Keycloak from "keycloak-js";

const keycloak = new Keycloak({
  url: process.env.REACT_APP_KeyCloakServerUrl,// Keycloak base URL
  realm: process.env.REACT_APP_KeyCloakRealm, // realm name
  clientId: process.env.REACT_APP_KeyCloakClientId, // client ID
});

export default keycloak;