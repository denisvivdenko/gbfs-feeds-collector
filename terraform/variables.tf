variable "bucket_name" {
  description = "Name of the S3 bucket"
  type        = string
}

variable "container_service_name" {
  description = "Name of the Lightsail container service running the crawler"
  type        = string
  default     = "gbfs-feeds-collector"
}

variable "container_service_power" {
  description = "Lightsail container service power (nano, micro, small, ...)"
  type        = string
  default     = "nano"
}

variable "container_image" {
  description = "Image reference for the deployment, produced by `aws lightsail push-container-image` (e.g. \":gbfs-feeds-collector.app.1\")"
  type        = string
  default     = ""
}