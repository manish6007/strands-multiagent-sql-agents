# Provider Definition
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ==========================================
# 1. NETWORKING MODULE (VPC)
# ==========================================
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "${var.project_name}-vpc-${var.environment}"
    Environment = var.environment
  }
}

resource "aws_subnet" "public_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "${var.aws_region}a"
  map_public_ip_on_launch = true

  tags = { Name = "${var.project_name}-public-subnet-a" }
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = "${var.aws_region}a"

  tags = { Name = "${var.project_name}-private-subnet-a" }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.project_name}-igw" }
}

resource "aws_route_table" "public_rt" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }
}

resource "aws_route_table_association" "public_assoc" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public_rt.id
}


# ==========================================
# 2. S3 BUCKET (Parquet & Query Results)
# ==========================================
resource "aws_s3_bucket" "data_lake" {
  bucket        = "${var.project_name}-data-lake-${var.environment}"
  force_destroy = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "lake_enc" {
  bucket = aws_s3_bucket.data_lake.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}


# ==========================================
# 3. AMAZON ATHENA METADATA & DATABASE
# ==========================================
resource "aws_athena_database" "analytics" {
  name   = "analytics_db_${var.environment}"
  bucket = aws_s3_bucket.data_lake.id
}

resource "aws_athena_workgroup" "analytics_wg" {
  name = "${var.project_name}-workgroup"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.data_lake.bucket}/query_results/"
      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }
}


# ==========================================
# 4. RDS POSTGRES (with pgvector support)
# ==========================================
resource "aws_db_subnet_group" "db_subnets" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.public_a.id] # Multi-AZ simulated
}

resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg"
  description = "Allow inbound PostgreSQL traffic"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "PostgreSQL"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [aws_vpc.main.cidr_block]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "pgvector" {
  allocated_storage      = 20
  max_allocated_storage  = 100
  db_name                = "postgres"
  engine                 = "postgres"
  engine_version         = "16.1"
  instance_class         = "db.t4g.micro"
  username               = "postgres"
  password               = aws_secretsmanager_secret_version.db_pwd.secret_string
  db_subnet_group_name   = aws_db_subnet_group.db_subnets.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  skip_final_snapshot    = true
}


# ==========================================
# 5. COGNITO USER POOL (Authentication)
# ==========================================
resource "aws_cognito_user_pool" "pool" {
  name = "${var.project_name}-user-pool-${var.environment}"

  password_policy {
    minimum_length    = 8
    require_lowercase = true
    require_numbers   = true
    require_symbols   = true
    require_uppercase = true
  }
}

resource "aws_cognito_user_pool_client" "client" {
  name         = "${var.project_name}-app-client"
  user_pool_id = aws_cognito_user_pool.pool.id

  generate_secret = false
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH"
  ]
}


# ==========================================
# 6. SECRETS MANAGER (Database Credentials)
# ==========================================
resource "aws_secretsmanager_secret" "db_secret" {
  name = "${var.project_name}-db-credentials-${var.environment}"
}

resource "aws_secretsmanager_secret_version" "db_pwd" {
  secret_id     = aws_secretsmanager_secret.db_secret.id
  secret_string = "db-password-12345678" # Managed dynamically in prod
}


# ==========================================
# 7. ECS FARGATE (Backend & Frontend services)
# ==========================================
resource "aws_ecs_cluster" "cluster" {
  name = "${var.project_name}-cluster-${var.environment}"
}

# Task Role providing access to Bedrock, S3, Athena
resource "aws_iam_role" "ecs_task_role" {
  name = "${var.project_name}-ecs-task-role"

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

resource "aws_iam_policy" "agent_permissions" {
  name        = "${var.project_name}-agent-policy"
  description = "Allows agents running on Fargate to call Bedrock, Athena, and read S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:ListFoundationModels"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:ListWorkGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.data_lake.arn,
          "${aws_s3_bucket.data_lake.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "task_policy" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.agent_permissions.arn
}
