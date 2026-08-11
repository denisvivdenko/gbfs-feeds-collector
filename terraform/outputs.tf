output "container_service_url" {
  description = "Lightsail console URL for the container service"
  value       = "https://lightsail.aws.amazon.com/ls/webapp/eu-west-3/container-services/${aws_lightsail_container_service.crawler.name}"
}

output "crawler_access_key_id" {
  description = "Access key ID for the crawler's scoped S3 writer IAM user"
  value       = aws_iam_access_key.crawler.id
}

output "crawler_secret_access_key" {
  description = "Secret access key for the crawler's scoped S3 writer IAM user"
  value       = aws_iam_access_key.crawler.secret
  sensitive   = true
}
