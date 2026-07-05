variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS target deployment region"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Application deployment environment (dev, staging, prod)"
}

variable "project_name" {
  type        = string
  default     = "sql-agent"
  description = "The project name prefix applied to AWS resource tags"
}
