IMAGE := gbfs-feeds-collector

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
