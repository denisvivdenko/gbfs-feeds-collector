terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "eu-west-3"
}

resource "aws_s3_bucket" "data" {
  bucket = var.bucket_name
}

# Lightsail container services can't assume an IAM role, so we give the
# crawler a dedicated user scoped to just this bucket instead.
resource "aws_iam_user" "crawler" {
  name = "${var.container_service_name}-s3-writer"
}

resource "aws_iam_user_policy" "crawler_s3_write" {
  name = "${var.container_service_name}-s3-write"
  user = aws_iam_user.crawler.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:ListBucket"]
        Resource = [
          aws_s3_bucket.data.arn,
          "${aws_s3_bucket.data.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_access_key" "crawler" {
  user = aws_iam_user.crawler.name
}

resource "aws_lightsail_container_service" "crawler" {
  name        = var.container_service_name
  power       = var.container_service_power
  scale       = 1
  is_disabled = false
}

# Push the image first with:
#   aws lightsail push-container-image --service-name <name> --label app --image gbfs-feeds-collector:latest
# then set container_image (e.g. ":gbfs-feeds-collector.app.1") before applying this resource.
resource "aws_lightsail_container_service_deployment_version" "crawler" {
  service_name = aws_lightsail_container_service.crawler.name

  container {
    container_name = "gbfs-feeds-collector"
    image          = var.container_image

    environment = {
      STORAGE               = "s3"
      S3_BUCKET             = var.bucket_name
      AWS_REGION            = "eu-west-3"
      AWS_ACCESS_KEY_ID     = aws_iam_access_key.crawler.id
      AWS_SECRET_ACCESS_KEY = aws_iam_access_key.crawler.secret
    }
  }
}