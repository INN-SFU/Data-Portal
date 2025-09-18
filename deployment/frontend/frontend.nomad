job "frontend-application" {
  datacenters = ["rmcintos-cedar-cloud"]
  type        = "service"

  group "frontend-group" {
    network {
      port "http" {
        static = 80
      }
    }

    count = 1

    task "frontend" {
      driver = "docker"

      config {
        image      = "registry.rcg.sfu.ca/rcg/inn-data-portal/frontend:latest"
        auth {
      		username       = "INN-Data-Portal"
      		password       = "glpat-9VJ09YDZr0vTCZ-I0h4U7G86MQp1OjEzbgk.01.0z1li8v46"    # has read_registry scope
      		server_address = "https://registry.rcg.sfu.ca"
    			}
        force_pull = true
        ports      = ["http"]
      }

      template {
        data        = <<EOF
        #API_GATEWAY_STG={{- range nomadService "api-gateway-staging" }}http://{{ .Address }}:{{ .Port }}{{- end }}
        API_GATEWAY="http://127.0.0.1:65535"
        EOF
        destination = "local/env.txt"
        env         = true
      }

      env = {
        CI_ENVIRONMENT_NAME = "production"
        SERVER_NAME         = "inn.rmcintos.cedar.researchcomputinggroup.ca"
      }

      resources {
        cpu    = 500 # 500 MHz
        memory = 512 # 512MB
      }

      service {
        name     = "frontend-service-staging"
        provider = "nomad"
        port     = "http"
        tags = [
          "frontend",
          "traefik.enable=true",
          "traefik.http.routers.frontend.rule=Host(`inn.rmcintos.cedar.researchcomputinggroup.ca`)",
          "traefik.http.routers.frontend.entrypoints=websecure",
          "traefik.http.routers.frontend.tls=true",
          "traefik.http.services.frontend.loadbalancer.server.port=80"
        ]
        enable_tag_override = true
      }

      restart {
        attempts = 0
        interval = "30s"
        mode     = "delay"
      }
    }
  }
}
