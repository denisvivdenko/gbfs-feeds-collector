IMAGE := gbfs-feeds-collector
AWS_REGION ?= eu-west-3
ENV_FILE ?= .env.prod
LIGHTSAIL_SERVICE ?= gbfs-feeds-collector
LIGHTSAIL_LABEL ?= app

.PHONY: docker-build
docker-build:
	docker build -t $(IMAGE) .

.PHONY: crawl-local
crawl-local: docker-build
	docker run --rm \
		-e STORAGE=fs \
		-e LIMIT_PROVIDERS_CRAWLED=5 \
		-v $(CURDIR)/data:/app/data \
		$(IMAGE)

.PHONY: crawl-prod
crawl-prod: docker-build
ifndef S3_BUCKET
	$(error S3_BUCKET is required, e.g. make crawl-prod S3_BUCKET=my-bucket)
endif
ifeq (,$(wildcard $(ENV_FILE)))
	$(error $(ENV_FILE) not found. Copy .env.prod.example to $(ENV_FILE) and fill in AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY, or pass ENV_FILE=path/to/file)
endif
	docker run --rm \
		--env-file $(ENV_FILE) \
		-e STORAGE=s3 \
		-e S3_BUCKET=$(S3_BUCKET) \
		-e AWS_REGION=$(AWS_REGION) \
		$(IMAGE)


.PHONY: login-aws
login-aws:
	eval "$$(aws configure export-credentials --format env)"

.PHONY: lightsail-push
lightsail-push:
	docker build --platform linux/amd64 -t $(IMAGE):amd64 .
	aws lightsail push-container-image \
		--region $(AWS_REGION) \
		--service-name $(LIGHTSAIL_SERVICE) \
		--label $(LIGHTSAIL_LABEL) \
		--image $(IMAGE):amd64
