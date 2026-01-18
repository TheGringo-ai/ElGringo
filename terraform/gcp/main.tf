# 🚀 AI Team Platform - Google Cloud Platform Infrastructure
# Terraform configuration for complete GCP deployment

terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

# Provider configuration
provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# =============================================================================
# VARIABLES
# =============================================================================
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP Region"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP Zone"
  type        = string
  default     = "us-central1-a"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "ai_platform_image" {
  description = "AI Platform Docker image"
  type        = string
  default     = "gcr.io/PROJECT_ID/ai-team-platform:latest"
}

# =============================================================================
# ENABLE APIs
# =============================================================================
resource "google_project_service" "apis" {
  for_each = toset([
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "container.googleapis.com",
    "run.googleapis.com",
    "cloudsql.googleapis.com",
    "sqladmin.googleapis.com",
    "redis.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
    "cloudbuild.googleapis.com",
    "containerregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "iamcredentials.googleapis.com"
  ])

  project = var.project_id
  service = each.value
  
  disable_dependent_services = false
  disable_on_destroy         = false
}

# =============================================================================
# NETWORKING
# =============================================================================
resource "google_compute_network" "ai_platform_vpc" {
  name                    = "ai-platform-vpc"
  auto_create_subnetworks = false
  routing_mode           = "GLOBAL"
  
  depends_on = [google_project_service.apis]
}

resource "google_compute_subnetwork" "ai_platform_subnet" {
  name          = "ai-platform-subnet"
  ip_cidr_range = "10.0.0.0/16"
  region        = var.region
  network       = google_compute_network.ai_platform_vpc.id
  
  # Secondary ranges for GKE
  secondary_ip_range {
    range_name    = "gke-pods"
    ip_cidr_range = "10.1.0.0/16"
  }
  
  secondary_ip_range {
    range_name    = "gke-services"
    ip_cidr_range = "10.2.0.0/16"
  }
}

# Cloud Router for NAT
resource "google_compute_router" "ai_platform_router" {
  name    = "ai-platform-router"
  region  = var.region
  network = google_compute_network.ai_platform_vpc.id
}

# Cloud NAT
resource "google_compute_router_nat" "ai_platform_nat" {
  name               = "ai-platform-nat"
  router             = google_compute_router.ai_platform_router.name
  region             = var.region
  nat_ip_allocate_option = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}

# Firewall rules
resource "google_compute_firewall" "allow_internal" {
  name    = "ai-platform-allow-internal"
  network = google_compute_network.ai_platform_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = ["10.0.0.0/8"]
}

resource "google_compute_firewall" "allow_http_https" {
  name    = "ai-platform-allow-http-https"
  network = google_compute_network.ai_platform_vpc.name

  allow {
    protocol = "tcp"
    ports    = ["80", "443", "8080"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["ai-platform", "http-server", "https-server"]
}

# =============================================================================
# CLOUD SQL (PostgreSQL)
# =============================================================================
resource "google_sql_database_instance" "ai_platform_db" {
  name             = "ai-platform-db-${var.environment}"
  database_version = "POSTGRES_15"
  region           = var.region
  
  settings {
    tier              = "db-custom-2-4096"
    availability_type = "REGIONAL"
    
    backup_configuration {
      enabled                        = true
      start_time                     = "03:00"
      location                      = var.region
      point_in_time_recovery_enabled = true
      transaction_log_retention_days = 7
      backup_retention_settings {
        retained_backups = 30
      }
    }
    
    ip_configuration {
      ipv4_enabled    = true
      private_network = google_compute_network.ai_platform_vpc.id
      require_ssl     = true
    }
    
    database_flags {
      name  = "max_connections"
      value = "200"
    }
    
    maintenance_window {
      day          = 7
      hour         = 3
      update_track = "stable"
    }
    
    insights_config {
      query_insights_enabled  = true
      record_application_tags = true
      record_client_address   = true
    }
  }
  
  deletion_protection = true
  
  depends_on = [google_project_service.apis]
}

resource "google_sql_database" "ai_platform_database" {
  name     = "aiplatform_db"
  instance = google_sql_database_instance.ai_platform_db.name
}

resource "google_sql_user" "ai_platform_user" {
  name     = "aiplatform"
  instance = google_sql_database_instance.ai_platform_db.name
  password = random_password.db_password.result
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# =============================================================================
# REDIS (MEMORYSTORE)
# =============================================================================
resource "google_redis_instance" "ai_platform_cache" {
  name               = "ai-platform-cache"
  memory_size_gb     = 4
  region             = var.region
  tier               = "STANDARD_HA"
  redis_version      = "REDIS_7_0"
  
  authorized_network = google_compute_network.ai_platform_vpc.id
  
  redis_configs = {
    maxmemory-policy = "allkeys-lru"
    notify-keyspace-events = "Ex"
  }
  
  depends_on = [google_project_service.apis]
}

# =============================================================================
# SECRETS MANAGER
# =============================================================================
resource "google_secret_manager_secret" "db_password" {
  secret_id = "ai-platform-db-password"
  
  replication {
    auto {}
  }
  
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
}

resource "google_secret_manager_secret" "api_keys" {
  for_each = toset([
    "openai-api-key",
    "anthropic-api-key", 
    "google-api-key",
    "secret-key"
  ])
  
  secret_id = "ai-platform-${each.value}"
  
  replication {
    auto {}
  }
}

# =============================================================================
# GOOGLE KUBERNETES ENGINE
# =============================================================================
resource "google_container_cluster" "ai_platform_gke" {
  name     = "ai-platform-gke"
  location = var.region
  
  # We can't create a cluster with no node pool defined, but we want to only use
  # separately managed node pools. So we create the smallest possible default
  # node pool and immediately delete it.
  remove_default_node_pool = true
  initial_node_count       = 1
  
  network    = google_compute_network.ai_platform_vpc.name
  subnetwork = google_compute_subnetwork.ai_platform_subnet.name
  
  # IP allocation for pods and services
  ip_allocation_policy {
    cluster_secondary_range_name  = "gke-pods"
    services_secondary_range_name = "gke-services"
  }
  
  # Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  # Network policy
  network_policy {
    enabled = true
  }
  
  # Master auth
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }
  
  # Addons
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
    network_policy_config {
      disabled = false
    }
  }
  
  depends_on = [google_project_service.apis]
}

resource "google_container_node_pool" "ai_platform_nodes" {
  name       = "ai-platform-nodes"
  location   = var.region
  cluster    = google_container_cluster.ai_platform_gke.name
  node_count = 3
  
  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }
  
  management {
    auto_repair  = true
    auto_upgrade = true
  }
  
  node_config {
    preemptible  = false
    machine_type = "e2-standard-4"
    
    # Google recommends custom service accounts that have cloud-platform scope and permissions granted via IAM Roles.
    service_account = google_service_account.gke_node_sa.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]
    
    labels = {
      env = var.environment
    }
    
    tags = ["ai-platform", "gke-node"]
    
    metadata = {
      disable-legacy-endpoints = "true"
    }
    
    workload_metadata_config {
      mode = "GKE_METADATA"
    }
  }
}

# =============================================================================
# CLOUD RUN (Alternative deployment option)
# =============================================================================
resource "google_cloud_run_service" "ai_platform_service" {
  name     = "ai-platform-service"
  location = var.region
  
  template {
    spec {
      containers {
        image = var.ai_platform_image
        
        ports {
          container_port = 8080
        }
        
        env {
          name  = "AI_PLATFORM_ENV"
          value = "production"
        }
        
        env {
          name  = "DATABASE_URL"
          value = "postgresql://${google_sql_user.ai_platform_user.name}:${random_password.db_password.result}@${google_sql_database_instance.ai_platform_db.private_ip_address}:5432/${google_sql_database.ai_platform_database.name}"
        }
        
        env {
          name  = "REDIS_URL"
          value = "redis://${google_redis_instance.ai_platform_cache.host}:${google_redis_instance.ai_platform_cache.port}"
        }
        
        resources {
          limits = {
            cpu    = "2000m"
            memory = "2Gi"
          }
        }
      }
      
      container_concurrency = 100
      timeout_seconds      = 3600
    }
    
    metadata {
      annotations = {
        "autoscaling.knative.dev/maxScale" = "100"
        "run.googleapis.com/vpc-access-connector" = google_vpc_access_connector.ai_platform_connector.id
      }
    }
  }
  
  traffic {
    percent         = 100
    latest_revision = true
  }
  
  depends_on = [google_project_service.apis]
}

# VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "ai_platform_connector" {
  name          = "ai-platform-connector"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = google_compute_network.ai_platform_vpc.name
}

# Make Cloud Run service public
resource "google_cloud_run_service_iam_member" "public" {
  location = google_cloud_run_service.ai_platform_service.location
  project  = google_cloud_run_service.ai_platform_service.project
  service  = google_cloud_run_service.ai_platform_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# =============================================================================
# IAM SERVICE ACCOUNTS
# =============================================================================
resource "google_service_account" "gke_node_sa" {
  account_id   = "gke-node-sa"
  display_name = "GKE Node Service Account"
}

resource "google_project_iam_member" "gke_node_sa_roles" {
  for_each = toset([
    "roles/logging.logWriter",
    "roles/monitoring.metricWriter",
    "roles/monitoring.viewer",
    "roles/stackdriver.resourceMetadata.writer"
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.gke_node_sa.email}"
}

resource "google_service_account" "ai_platform_sa" {
  account_id   = "ai-platform-sa"
  display_name = "AI Platform Service Account"
}

resource "google_project_iam_member" "ai_platform_sa_roles" {
  for_each = toset([
    "roles/cloudsql.client",
    "roles/secretmanager.secretAccessor",
    "roles/monitoring.metricWriter",
    "roles/logging.logWriter"
  ])
  
  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.ai_platform_sa.email}"
}

# =============================================================================
# MONITORING & LOGGING
# =============================================================================
resource "google_monitoring_alert_policy" "high_cpu_usage" {
  display_name = "High CPU Usage - AI Platform"
  combiner     = "OR"
  
  conditions {
    display_name = "CPU Usage > 80%"
    
    condition_threshold {
      filter          = "resource.type=\"gce_instance\""
      duration        = "300s"
      comparison      = "COMPARISON_GREATER_THAN"
      threshold_value = 0.8
      
      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_MEAN"
      }
    }
  }
  
  notification_channels = []
  
  depends_on = [google_project_service.apis]
}

# =============================================================================
# OUTPUTS
# =============================================================================
output "gke_cluster_name" {
  description = "GKE Cluster name"
  value       = google_container_cluster.ai_platform_gke.name
}

output "gke_cluster_endpoint" {
  description = "GKE Cluster endpoint"
  value       = google_container_cluster.ai_platform_gke.endpoint
  sensitive   = true
}

output "cloud_run_url" {
  description = "Cloud Run service URL"
  value       = google_cloud_run_service.ai_platform_service.status[0].url
}

output "database_connection" {
  description = "Database connection info"
  value = {
    host     = google_sql_database_instance.ai_platform_db.private_ip_address
    database = google_sql_database.ai_platform_database.name
    username = google_sql_user.ai_platform_user.name
  }
  sensitive = true
}

output "redis_host" {
  description = "Redis host"
  value       = google_redis_instance.ai_platform_cache.host
}

output "vpc_network" {
  description = "VPC network name"
  value       = google_compute_network.ai_platform_vpc.name
}