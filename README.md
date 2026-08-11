# gbfs-feeds-collector

Crawls [GBFS](https://gbfs.org/) providers listed in `data/gbfs_providers.csv`, fetches each
provider's feeds, and saves the raw JSON payloads to a storage backend (local filesystem or S3).

## Requirements

- Docker (for the containerized workflows below), or Python 3.11+ with [uv](https://docs.astral.sh/uv/) for running directly on the host
- AWS CLI v2, authenticated, if you're writing to S3 or deploying to Lightsail

## Running locally

### With Docker (recommended)

```bash
make crawl-local
```

Builds the image and runs the crawler as a long-running service against the local
filesystem, limited to 5 providers, writing output to `./data/gbfs_feeds`. Each feed
name is crawled on its own interval, per `data/feeds_schedule.yaml`. Stop it with
Ctrl+C.

### Without Docker

```bash
uv sync
uv run python -m gbfs_feeds_collector.pipelines.collect_data_from_gbfs_feeds \
  --storage local --limit 5
```

Useful CLI flags (see `--help` for the full list):

| Flag | Description |
| --- | --- |
| `--storage {local,s3}` | Storage backend (default: `local`) |
| `--output-path PATH` | Output directory for local storage (default: `data/gbfs_feeds`) |
| `--s3-bucket NAME` | Required when `--storage s3` |
| `--limit N` | Max number of providers to crawl (default: no limit) |
| `--concurrency N` | Max concurrent HTTP requests (default: 20) |
| `--providers-csv-path PATH` | Providers CSV to read (default: `data/gbfs_providers.csv`) |
| `--feeds-schedule-path PATH` | YAML file mapping feed name to crawl interval in seconds; feed names not listed are skipped entirely (default: `data/feeds_schedule.yaml`) |
| `--max-cycles N` | Number of crawl cycles to run per feed before exiting (default: run forever) |

Each feed name (`station_status`, `station_information`, ...) is crawled on its own
schedule, independent of every other feed name, driven by `data/feeds_schedule.yaml`:

```yaml
station_status: 60      # crawl every 60s
station_information: 3600  # crawl every hour
```

Without `--max-cycles`, the process is the schedule — it runs forever, crawling each
feed name whenever its own interval elapses. The Docker image (`entrypoint.sh`) just
execs this directly, so it's a long-running service controlled by env vars:

| Env var | Description |
| --- | --- |
| `STORAGE` | `fs` (local) or `s3` (default: `fs`) |
| `S3_BUCKET` | Required when `STORAGE=s3` |
| `LIMIT_PROVIDERS_CRAWLED` | Max providers per run (default: no limit) |

### Against S3, locally

```bash
cp .env.prod.example .env.prod   # fill in AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
make crawl-prod S3_BUCKET=my-bucket
```

### Tests

```bash
uv run pytest
```

The `stress` marker (real GBFS endpoints, used for performance benchmarking) is excluded by
default; run it explicitly with `uv run pytest -m stress`.

## Deploying to AWS Lightsail

Infrastructure lives in `terraform/` and provisions:

- an S3 bucket for raw feed payloads (`aws_s3_bucket.data`)
- a Lightsail Container Service running the crawler loop (`aws_lightsail_container_service.crawler`)
- an IAM user scoped to `PutObject`/`ListBucket` on just that bucket, whose access key is
  injected into the container as `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` (Lightsail
  containers can't assume IAM roles, unlike ECS/EC2)

The service has no public endpoint — it's a background worker, not an HTTP service.

### First-time setup

1. Authenticate the AWS CLI (`aws login` or `aws configure`), then initialize Terraform:

   ```bash
   cd terraform
   terraform init
   ```

2. Create the Lightsail service and IAM access key first — the image push in the next step
   needs the service to already exist as a push target:

   ```bash
   terraform apply -target=aws_lightsail_container_service.crawler -target=aws_iam_access_key.crawler
   ```

3. Build and push the image to the service's private registry:

   ```bash
   cd ..
   eval "$(aws configure export-credentials --format env)"
   make lightsail-push
   ```

   > `push-container-image` shells out to a separate `lightsailctl` plugin that only understands
   > classic AWS credentials (env vars / `~/.aws/credentials`) — it can't read the newer
   > `aws login` session cache, so the `eval` above is required even if `aws sts
   > get-caller-identity` already works.

   This prints a reference like `:gbfs-feeds-collector.app.1` — copy it.

4. Set that reference in `terraform/terraform.tfvars`:

   ```hcl
   container_image = ":gbfs-feeds-collector.app.1"
   ```

5. Deploy:

   ```bash
   cd terraform
   terraform apply
   ```

Check status and logs at the URL in the `container_service_url` output, or:

```bash
terraform output container_service_url
```

### Redeploying after a code change

```bash
eval "$(aws configure export-credentials --format env)"
make lightsail-push          # note the new :gbfs-feeds-collector.app.N reference it prints
# update container_image in terraform/terraform.tfvars to that reference
cd terraform && terraform apply
```

### Terraform variables

| Variable | Description | Default |
| --- | --- | --- |
| `bucket_name` | S3 bucket name | — (required) |
| `container_service_name` | Lightsail container service name | `gbfs-feeds-collector` |
| `container_service_power` | Lightsail power tier (`nano`, `micro`, `small`, ...) | `nano` |
| `container_image` | Image reference from `push-container-image` | — (required) |
