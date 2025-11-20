locals {
  server-name = "keycloak.rmcintos.cedar.researchcomputinggroup.ca"
}

job "keycloak-app" {
  datacenters = ["rmcintos-cedar-cloud"]
  type        = "service"

  group "keycloak-group" {
    network {
      port "keycloak-http" {
        to = 8080
      }
      port "keycloak-https" {
        to = 443
      }
      port "db" {
        to = 3306
      }
    }

    count = 1
    constraint {
      attribute = "${node.unique.name}"
      operator  = "="
      value     = "nomad-client-1"
    }

    volume "keycloak-data" {
      type      = "host"
      source    = "keycloak-data"
      read_only = false # Mount as read-only
    }

    volume "mysql-data" {
      type      = "host"
      source    = "mysql-data"
      read_only = false # Mount as read-only
    }

    task "keycloak" {
      driver = "docker"

      config {
        image   = "quay.io/keycloak/keycloak:26.2"
        command = "start-dev"
        args    = [
          				 "--import-realm", 
          				 "--proxy-headers", "xforwarded", 
           				 "--http-max-queued-requests", "100", 
            			 "--log-level=org.keycloak.social.user_profile_dump:DEBUG", 
        					]
        # Args are for prod: https://www.keycloak.org/server/configuration-production
        # TODO: https and tls for secure communication
        # Hostname for keycloak via env var
        # TODO: Exposing the Keycloak Administration APIs and UI on a different hostname
        # Proxy headers for traefik reverse proxy
        # TODO: Enable sticky sessions for reverse proxies
        # http-max-request to limit the number of queued requests
        # Production grade database by `keycloak-db` service

        #volumes = [
        #  "keycloak-data:/opt/keycloak/data/import/"
        #]
        ports = ["keycloak-http", "keycloak-https"]
      }

      env = {
        KEYCLOAK_ADMIN          = "admin"
        KEYCLOAK_ADMIN_PASSWORD = "admin"
        #DB_VENDOR            = "MYSQL"
        #DB_ADDR              = ""
        #DB_DATABASE          = "keycloak"
        #DB_USER              = "keycloak"
        #DB_PASSWORD          = "password"
        KC_DB              = "mysql"
        KC_DB_URL_DATABASE = "keycloak"
        KC_DB_USERNAME     = "keycloak"
        KC_DB_PASSWORD     = "password"
        # KC_LOG_LEVEL         = "debug"
        KC_HOSTNAME        = "${local.server-name}"
        KC_HEALTH_ENABLED  = "true"
        KC_METRICS_ENABLED = "true"
        # If the server should expose /health check and /metrics endpoints.
      }

      template {
        data        = <<EOF
        KC_DB_URL_HOST={{- range nomadService "keycloak-db" }}{{ .Address }}{{- end }}
        KC_DB_URL_PORT={{- range nomadService "keycloak-db" }}{{ .Port }}{{- end }}
    		KC_DB_URL=jdbc:${KC_DB}://${KC_DB_URL_HOST}:${KC_DB_URL_PORT}/${KC_DB_URL_DATABASE}?characterEncoding=UTF-8
        EOF
        destination = "local/db-server.env"
        env         = true
      }

      volume_mount {
        volume      = "keycloak-data"
        destination = "/opt/keycloak/data/import" # Target inside the container
        read_only   = false
      }

      resources {
        cpu    = 2048 # 500 MHz
        memory = 2048 # 512MB
      }

      service {
        name     = "keycloak-service"
        provider = "nomad"
        port     = "keycloak-http"
        tags = [
          "keycloak",
          "traefik.enable=true",
          "traefik.http.routers.keycloak.rule=Host(`${local.server-name}`)",
          "traefik.http.routers.keycloak-nossl.rule=Host(`${local.server-name}`)",
          "traefik.http.routers.keycloak.tls=true",
        ]

        enable_tag_override = true
      }

      #      restart {
      #        attempts = 0
      #        interval = "30s"
      #        mode     = "delay"
      #      }

    }


    task "keycloak-mysql" {
      driver = "docker"
      config {
        image = "mysql/mysql-server:8.0"
        ports = ["db"]

        volumes = [
          "docker-entrypoint-initdb.d/:/docker-entrypoint-initdb.d/",
          # "mysql-data/:/var/lib/mysql",
        ]
      }

      env = {
        MYSQL_ROOT_PASSWORD = "my-secret-pw"
        DB_PASSWORD         = "password"
      }

      template {
        data        = <<EOH
        CREATE DATABASE keycloak;
        CREATE USER 'keycloak'@'%' IDENTIFIED BY '{{ env "DB_PASSWORD" }}';
        GRANT ALL PRIVILEGES ON keycloak.* TO 'keycloak'@'%';
        EOH
        destination = "/docker-entrypoint-initdb.d/db.sql"
      }

      resources {
        cpu    = 1000
        memory = 2048
      }

      service {
        name     = "keycloak-db"
        provider = "nomad"
        port     = "db"
        tags = [
          "keycloak-db",
          "traefik.enable=true",
        ]
      }

      volume_mount {
        volume      = "mysql-data"
        destination = "/var/lib/mysql" # Target inside the container
        read_only   = false
      }
    }

  }
}
