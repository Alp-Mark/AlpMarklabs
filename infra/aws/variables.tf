variable "aws_region" {
  description = "AWS region for the AlpMark base infrastructure."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Short project name used in AWS resource names."
  type        = string
  default     = "alpmark"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "dev"
}

variable "vpc_cidr" {
  description = "CIDR block for the base VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "log_retention_days" {
  description = "CloudWatch log retention for ECS workloads."
  type        = number
  default     = 14
}
