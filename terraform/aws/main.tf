# 🚀 AI Team Platform - AWS Infrastructure
# Terraform configuration for complete AWS deployment

terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

# Provider configuration
provider "aws" {
  region = var.region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "ai-team-platform"
      ManagedBy   = "terraform"
    }
  }
}

# =============================================================================
# VARIABLES
# =============================================================================
variable "region" {
  description = "AWS Region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "ai_platform_image" {
  description = "AI Platform Docker image"
  type        = string
  default     = "ai-team-platform:latest"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = ""
}

# =============================================================================
# DATA SOURCES
# =============================================================================
data "aws_availability_zones" "available" {
  state = "available"
}

data "aws_caller_identity" "current" {}

# =============================================================================
# VPC AND NETWORKING
# =============================================================================
resource "aws_vpc" "ai_platform_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "ai-platform-vpc"
  }
}

resource "aws_internet_gateway" "ai_platform_igw" {
  vpc_id = aws_vpc.ai_platform_vpc.id
  
  tags = {
    Name = "ai-platform-igw"
  }
}

resource "aws_subnet" "ai_platform_public" {
  count = 2
  
  vpc_id                  = aws_vpc.ai_platform_vpc.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
  
  tags = {
    Name = "ai-platform-public-${count.index + 1}"
    Type = "public"
  }
}

resource "aws_subnet" "ai_platform_private" {
  count = 2
  
  vpc_id            = aws_vpc.ai_platform_vpc.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
  
  tags = {
    Name = "ai-platform-private-${count.index + 1}"
    Type = "private"
  }
}

# NAT Gateways
resource "aws_eip" "ai_platform_nat" {
  count = 2
  
  domain = "vpc"
  
  tags = {
    Name = "ai-platform-nat-${count.index + 1}"
  }
}

resource "aws_nat_gateway" "ai_platform_nat" {
  count = 2
  
  allocation_id = aws_eip.ai_platform_nat[count.index].id
  subnet_id     = aws_subnet.ai_platform_public[count.index].id
  
  tags = {
    Name = "ai-platform-nat-${count.index + 1}"
  }
  
  depends_on = [aws_internet_gateway.ai_platform_igw]
}

# Route Tables
resource "aws_route_table" "ai_platform_public" {
  vpc_id = aws_vpc.ai_platform_vpc.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.ai_platform_igw.id
  }
  
  tags = {
    Name = "ai-platform-public-rt"
  }
}

resource "aws_route_table" "ai_platform_private" {
  count = 2
  
  vpc_id = aws_vpc.ai_platform_vpc.id
  
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.ai_platform_nat[count.index].id
  }
  
  tags = {
    Name = "ai-platform-private-rt-${count.index + 1}"
  }
}

# Route Table Associations
resource "aws_route_table_association" "ai_platform_public" {
  count = 2
  
  subnet_id      = aws_subnet.ai_platform_public[count.index].id
  route_table_id = aws_route_table.ai_platform_public.id
}

resource "aws_route_table_association" "ai_platform_private" {
  count = 2
  
  subnet_id      = aws_subnet.ai_platform_private[count.index].id
  route_table_id = aws_route_table.ai_platform_private[count.index].id
}

# =============================================================================
# SECURITY GROUPS
# =============================================================================
resource "aws_security_group" "ai_platform_alb" {
  name_prefix = "ai-platform-alb-"
  vpc_id      = aws_vpc.ai_platform_vpc.id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "ai-platform-alb-sg"
  }
}

resource "aws_security_group" "ai_platform_ecs" {
  name_prefix = "ai-platform-ecs-"
  vpc_id      = aws_vpc.ai_platform_vpc.id
  
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.ai_platform_alb.id]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "ai-platform-ecs-sg"
  }
}

resource "aws_security_group" "ai_platform_rds" {
  name_prefix = "ai-platform-rds-"
  vpc_id      = aws_vpc.ai_platform_vpc.id
  
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ai_platform_ecs.id]
  }
  
  tags = {
    Name = "ai-platform-rds-sg"
  }
}

resource "aws_security_group" "ai_platform_redis" {
  name_prefix = "ai-platform-redis-"
  vpc_id      = aws_vpc.ai_platform_vpc.id
  
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ai_platform_ecs.id]
  }
  
  tags = {
    Name = "ai-platform-redis-sg"
  }
}

# =============================================================================
# RDS (POSTGRESQL)
# =============================================================================
resource "aws_db_subnet_group" "ai_platform_db_subnet_group" {
  name       = "ai-platform-db-subnet-group"
  subnet_ids = aws_subnet.ai_platform_private[*].id
  
  tags = {
    Name = "ai-platform-db-subnet-group"
  }
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

resource "aws_db_instance" "ai_platform_db" {
  identifier = "ai-platform-db"
  
  engine         = "postgres"
  engine_version = "15.4"
  instance_class = "db.t3.medium"
  
  allocated_storage     = 100
  max_allocated_storage = 1000
  storage_type         = "gp3"
  storage_encrypted    = true
  
  db_name  = "aiplatform_db"
  username = "aiplatform"
  password = random_password.db_password.result
  
  vpc_security_group_ids = [aws_security_group.ai_platform_rds.id]
  db_subnet_group_name   = aws_db_subnet_group.ai_platform_db_subnet_group.name
  
  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = false
  final_snapshot_identifier = "ai-platform-db-final-snapshot"
  
  performance_insights_enabled = true
  monitoring_interval         = 60
  monitoring_role_arn        = aws_iam_role.rds_enhanced_monitoring.arn
  
  tags = {
    Name = "ai-platform-db"
  }
}

# =============================================================================
# ELASTICACHE (REDIS)
# =============================================================================
resource "aws_elasticache_subnet_group" "ai_platform_redis_subnet_group" {
  name       = "ai-platform-redis-subnet-group"
  subnet_ids = aws_subnet.ai_platform_private[*].id
}

resource "aws_elasticache_replication_group" "ai_platform_redis" {
  replication_group_id       = "ai-platform-redis"
  description                = "AI Platform Redis cluster"
  
  node_type                  = "cache.t3.medium"
  port                       = 6379
  parameter_group_name       = "default.redis7"
  
  num_cache_clusters         = 2
  automatic_failover_enabled = true
  multi_az_enabled          = true
  
  subnet_group_name = aws_elasticache_subnet_group.ai_platform_redis_subnet_group.name
  security_group_ids = [aws_security_group.ai_platform_redis.id]
  
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  
  tags = {
    Name = "ai-platform-redis"
  }
}

# =============================================================================
# ECR REPOSITORY
# =============================================================================
resource "aws_ecr_repository" "ai_platform_repo" {
  name                 = "ai-team-platform"
  image_tag_mutability = "MUTABLE"
  
  image_scanning_configuration {
    scan_on_push = true
  }
  
  encryption_configuration {
    encryption_type = "AES256"
  }
  
  lifecycle_policy {
    policy = jsonencode({
      rules = [
        {
          rulePriority = 1
          description  = "Keep last 10 images"
          selection = {
            tagStatus = "any"
            countType = "imageCountMoreThan"
            countNumber = 10
          }
          action = {
            type = "expire"
          }
        }
      ]
    })
  }
}

# =============================================================================
# ECS CLUSTER
# =============================================================================
resource "aws_ecs_cluster" "ai_platform_cluster" {
  name = "ai-platform-cluster"
  
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
  
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight           = 70
    base            = 2
  }
  
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE_SPOT"
    weight           = 30
  }
  
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
  
  tags = {
    Name = "ai-platform-cluster"
  }
}

# =============================================================================
# ECS TASK DEFINITION
# =============================================================================
resource "aws_ecs_task_definition" "ai_platform_task" {
  family                   = "ai-platform-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "2048"
  memory                   = "4096"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn
  
  container_definitions = jsonencode([
    {
      name  = "ai-platform"
      image = "${aws_ecr_repository.ai_platform_repo.repository_url}:latest"
      
      portMappings = [
        {
          containerPort = 8080
          hostPort      = 8080
          protocol      = "tcp"
        }
      ]
      
      environment = [
        {
          name  = "AI_PLATFORM_ENV"
          value = "production"
        },
        {
          name  = "PORT"
          value = "8080"
        }
      ]
      
      secrets = [
        {
          name      = "DATABASE_URL"
          valueFrom = aws_secretsmanager_secret.db_connection.arn
        },
        {
          name      = "REDIS_URL"
          valueFrom = aws_secretsmanager_secret.redis_connection.arn
        },
        {
          name      = "SECRET_KEY"
          valueFrom = aws_secretsmanager_secret.app_secret.arn
        }
      ]
      
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.ai_platform_logs.name
          "awslogs-region"        = var.region
          "awslogs-stream-prefix" = "ecs"
        }
      }
      
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8080/health || exit 1"]
        interval    = 30
        timeout     = 5
        retries     = 3
        startPeriod = 60
      }
      
      essential = true
    }
  ])
}

# =============================================================================
# ECS SERVICE
# =============================================================================
resource "aws_ecs_service" "ai_platform_service" {
  name            = "ai-platform-service"
  cluster         = aws_ecs_cluster.ai_platform_cluster.id
  task_definition = aws_ecs_task_definition.ai_platform_task.arn
  desired_count   = 3
  launch_type     = "FARGATE"
  
  network_configuration {
    subnets         = aws_subnet.ai_platform_private[*].id
    security_groups = [aws_security_group.ai_platform_ecs.id]
  }
  
  load_balancer {
    target_group_arn = aws_lb_target_group.ai_platform_tg.arn
    container_name   = "ai-platform"
    container_port   = 8080
  }
  
  depends_on = [aws_lb_listener.ai_platform_listener]
  
  tags = {
    Name = "ai-platform-service"
  }
}

# =============================================================================
# APPLICATION LOAD BALANCER
# =============================================================================
resource "aws_lb" "ai_platform_alb" {
  name               = "ai-platform-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.ai_platform_alb.id]
  subnets            = aws_subnet.ai_platform_public[*].id
  
  enable_deletion_protection = false
  
  tags = {
    Name = "ai-platform-alb"
  }
}

resource "aws_lb_target_group" "ai_platform_tg" {
  name     = "ai-platform-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = aws_vpc.ai_platform_vpc.id
  target_type = "ip"
  
  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 10
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "ai_platform_listener" {
  load_balancer_arn = aws_lb.ai_platform_alb.arn
  port              = "80"
  protocol          = "HTTP"
  
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.ai_platform_tg.arn
  }
}

# =============================================================================
# SECRETS MANAGER
# =============================================================================
resource "aws_secretsmanager_secret" "db_connection" {
  name = "ai-platform/db-connection"
}

resource "aws_secretsmanager_secret_version" "db_connection" {
  secret_id = aws_secretsmanager_secret.db_connection.id
  secret_string = "postgresql://${aws_db_instance.ai_platform_db.username}:${random_password.db_password.result}@${aws_db_instance.ai_platform_db.endpoint}/${aws_db_instance.ai_platform_db.db_name}"
}

resource "aws_secretsmanager_secret" "redis_connection" {
  name = "ai-platform/redis-connection"
}

resource "aws_secretsmanager_secret_version" "redis_connection" {
  secret_id = aws_secretsmanager_secret.redis_connection.id
  secret_string = "redis://${aws_elasticache_replication_group.ai_platform_redis.primary_endpoint_address}:6379"
}

resource "aws_secretsmanager_secret" "app_secret" {
  name = "ai-platform/app-secret"
}

resource "aws_secretsmanager_secret_version" "app_secret" {
  secret_id = aws_secretsmanager_secret.app_secret.id
  secret_string = random_password.app_secret.result
}

resource "random_password" "app_secret" {
  length  = 64
  special = true
}

# =============================================================================
# IAM ROLES
# =============================================================================
resource "aws_iam_role" "ecs_execution_role" {
  name = "ai-platform-ecs-execution-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_secrets_policy" {
  name = "ecs-execution-secrets-policy"
  role = aws_iam_role.ecs_execution_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.db_connection.arn,
          aws_secretsmanager_secret.redis_connection.arn,
          aws_secretsmanager_secret.app_secret.arn
        ]
      }
    ]
  })
}

resource "aws_iam_role" "ecs_task_role" {
  name = "ai-platform-ecs-task-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role" "rds_enhanced_monitoring" {
  name = "rds-monitoring-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "rds_enhanced_monitoring" {
  role       = aws_iam_role.rds_enhanced_monitoring.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

# =============================================================================
# CLOUDWATCH
# =============================================================================
resource "aws_cloudwatch_log_group" "ai_platform_logs" {
  name              = "/aws/ecs/ai-platform"
  retention_in_days = 30
}

# =============================================================================
# AUTO SCALING
# =============================================================================
resource "aws_appautoscaling_target" "ai_platform_target" {
  max_capacity       = 20
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.ai_platform_cluster.name}/${aws_ecs_service.ai_platform_service.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "ai_platform_up" {
  name               = "ai-platform-scale-up"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ai_platform_target.resource_id
  scalable_dimension = aws_appautoscaling_target.ai_platform_target.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ai_platform_target.service_namespace
  
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# =============================================================================
# OUTPUTS
# =============================================================================
output "load_balancer_dns" {
  description = "DNS name of the load balancer"
  value       = aws_lb.ai_platform_alb.dns_name
}

output "load_balancer_hosted_zone_id" {
  description = "Hosted zone ID of the load balancer"
  value       = aws_lb.ai_platform_alb.zone_id
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.ai_platform_repo.repository_url
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.ai_platform_cluster.name
}

output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.ai_platform_vpc.id
}

output "database_endpoint" {
  description = "Database endpoint"
  value       = aws_db_instance.ai_platform_db.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis endpoint"
  value       = aws_elasticache_replication_group.ai_platform_redis.primary_endpoint_address
}