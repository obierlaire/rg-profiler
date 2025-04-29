# RG Profiler Makefile
# For building and managing Docker images

# Constants
DOCKER_BASE_NAME := rg-profiler
DOCKER_NETWORK_NAME := rg-profiler-network

# Database images
POSTGRES_IMAGE := $(DOCKER_BASE_NAME)-postgres
MYSQL_IMAGE := $(DOCKER_BASE_NAME)-mysql
MONGODB_IMAGE := $(DOCKER_BASE_NAME)-mongodb

# WRK benchmarking image
WRK_IMAGE := $(DOCKER_BASE_NAME)-wrk

# Base framework images
PYTHON_BASE_IMAGE := $(DOCKER_BASE_NAME)-python-base

# Helper targets
.PHONY: all
all: network databases wrk python-base

.PHONY: clean
clean: clean-databases clean-wrk clean-python-base
	@echo "Removed all RG Profiler Docker images"

.PHONY: clean-all
clean-all: clean-containers clean network-remove
	@echo "✅ Completely cleaned up RG Profiler environment"

# Create Docker network
.PHONY: network
network:
	@echo "Creating Docker network $(DOCKER_NETWORK_NAME)..."
	@docker network inspect $(DOCKER_NETWORK_NAME) >/dev/null 2>&1 || \
		docker network create $(DOCKER_NETWORK_NAME)
	@echo "✅ Network ready: $(DOCKER_NETWORK_NAME)"

# Remove Docker network
.PHONY: network-remove
network-remove:
	@echo "Removing Docker network $(DOCKER_NETWORK_NAME)..."
	@docker network rm $(DOCKER_NETWORK_NAME) 2>/dev/null || true
	@echo "✅ Network removed: $(DOCKER_NETWORK_NAME)"

# Database targets
.PHONY: databases
databases: postgres mysql mongodb

.PHONY: postgres
postgres:
	@echo "Building PostgreSQL image..."
	@docker build -t $(POSTGRES_IMAGE) -f docker/postgres/postgres.dockerfile docker/postgres
	@echo "✅ Built PostgreSQL image: $(POSTGRES_IMAGE)"

.PHONY: mysql
mysql:
	@echo "Building MySQL image..."
	@docker build -t $(MYSQL_IMAGE) -f docker/mysql/mysql.dockerfile docker/mysql
	@echo "✅ Built MySQL image: $(MYSQL_IMAGE)"

.PHONY: mongodb
mongodb:
	@echo "Building MongoDB image..."
	@docker build -t $(MONGODB_IMAGE) -f docker/mongodb/mongodb.dockerfile docker/mongodb || \
	(echo "Creating MongoDB Dockerfile..." && \
	echo "FROM mongo:latest\nCOPY init.js /docker-entrypoint-initdb.d/\nENV MONGO_INITDB_DATABASE=hello_world" > docker/mongodb/mongodb.dockerfile && \
	docker build -t $(MONGODB_IMAGE) -f docker/mongodb/mongodb.dockerfile docker/mongodb)
	@echo "✅ Built MongoDB image: $(MONGODB_IMAGE)"

.PHONY: clean-databases
clean-databases:
	@echo "Removing database images..."
	@docker rmi $(POSTGRES_IMAGE) $(MYSQL_IMAGE) $(MONGODB_IMAGE) 2>/dev/null || true

# WRK targets
.PHONY: wrk
wrk:
	@echo "Building WRK image..."
	@docker build -t $(WRK_IMAGE) docker/wrk
	@echo "✅ Built WRK image: $(WRK_IMAGE)"
	@echo "Note: This is a required pre-built image used by the profiler"
	@echo "WRK scripts will be mounted from the local 'wrk' directory at runtime"

.PHONY: clean-wrk
clean-wrk:
	@echo "Removing WRK image..."
	@docker rmi $(WRK_IMAGE) 2>/dev/null || true

.PHONY: run-wrk
run-wrk:
	@echo "Running WRK example test..."
	@docker run --rm \
		--name rg-profiler-wrk-test \
		--network $(DOCKER_NETWORK_NAME) \
		-v $(shell pwd)/wrk/profile:/scripts \
		$(WRK_IMAGE) \
		-t1 -c10 -d5s --latency \
		-s /scripts/json.lua \
		http://rg-profiler-postgres:5432

# Python base image
.PHONY: python-base
python-base:
	@echo "Building Python base image..."
	@docker build -t $(PYTHON_BASE_IMAGE) -f docker/base/Dockerfile.python docker/base
	@echo "✅ Built Python base image: $(PYTHON_BASE_IMAGE)"

.PHONY: clean-python-base
clean-python-base:
	@echo "Removing Python base image..."
	@docker rmi $(PYTHON_BASE_IMAGE) 2>/dev/null || true


# Start databases
.PHONY: start-databases
start-databases: network
	@echo "Starting database containers..."
	@echo "Ensuring network exists..."
	@docker network inspect $(DOCKER_NETWORK_NAME) >/dev/null 2>&1 || docker network create $(DOCKER_NETWORK_NAME)
	@echo "Starting PostgreSQL..."
	@docker-compose -f docker/docker-compose.postgres.yml up -d
	@echo "Starting MySQL..."
	@docker-compose -f docker/docker-compose.mysql.yml up -d
	@echo "Starting MongoDB..."
	@docker-compose -f docker/docker-compose.mongodb.yml up -d
	@echo "✅ All database containers started and connected to $(DOCKER_NETWORK_NAME) network"

# Stop databases
.PHONY: stop-databases
stop-databases:
	@echo "Stopping database containers..."
	@docker-compose -f docker/docker-compose.postgres.yml down
	@docker-compose -f docker/docker-compose.mysql.yml down
	@docker-compose -f docker/docker-compose.mongodb.yml down
	@echo "✅ All database containers stopped"

# Clean up all project containers
.PHONY: clean-containers
clean-containers:
	@echo "Cleaning up all project containers..."
	@echo "Stopping and removing all containers with name prefix '$(DOCKER_BASE_NAME)'..."
	@docker ps -a --filter "name=$(DOCKER_BASE_NAME)" -q | xargs -r docker rm -f
	@echo "✅ All project containers removed"

# Setup Python Virtual Environment
.PHONY: setup
setup:
	@echo "Setting up Python virtual environment..."
	@python -m venv venv
	@. venv/bin/activate && pip install -r requirements.txt
	@if [ -f .env ]; then \
		echo "Environment file found. To activate, run:"; \
		echo "source venv/bin/activate && source .env"; \
	else \
		echo "No .env file found. Please create one if needed."; \
		echo "To activate the environment, run:"; \
		echo "source venv/bin/activate"; \
	fi
	@echo "✅ Setup complete"

# Help
.PHONY: help
help:
	@echo "RG Profiler Makefile"
	@echo ""
	@echo "This Makefile helps you set up the infrastructure for RG Profiler,"
	@echo "a tool for benchmarking web frameworks for performance and energy consumption."
	@echo ""
	@echo "Targets:"
	@echo "  all                Build all infrastructure images (network, databases, wrk, python base)"
	@echo "  clean              Remove all Docker images"
	@echo "  clean-all          Stop all containers, remove images and network - complete cleanup"
	@echo "  network            Create Docker network for container communication"
	@echo "  network-remove     Remove Docker network"
	@echo "  databases          Build all database images"
	@echo "  postgres           Build PostgreSQL image"
	@echo "  mysql              Build MySQL image"
	@echo "  mongodb            Build MongoDB image"
	@echo "  clean-databases    Remove database images"
	@echo "  wrk                Build WRK benchmarking image"
	@echo "  run-wrk            Run WRK with an example benchmark"
	@echo "  clean-wrk          Remove WRK image"
	@echo "  python-base        Build Python base image with common dependencies"
	@echo "  clean-python-base  Remove Python base image"
	@echo "  start-databases    Start all database containers"
	@echo "  stop-databases     Stop all database containers"
	@echo "  clean-containers   Stop and remove all containers with the rg-profiler prefix"
	@echo "  setup              Set up Python virtual environment and install dependencies"
	@echo "  help               Show this help"
	@echo ""
	@echo "Architecture:"
	@echo "  1. Framework servers run in Docker containers with access to databases"
	@echo "  2. WRK generates load against each framework's endpoints"
	@echo "  3. Results are collected using Scalene (for profile mode) or"
	@echo "     CodeCarbon (for energy mode)"
	@echo ""
	@echo "Setup workflow:"
	@echo "  1. make setup            # Set up Python environment and dependencies"
	@echo "  2. make all              # Build all required infrastructure images"
	@echo "  3. make start-databases  # Start database containers on the network"
	@echo "  4. source venv/bin/activate # Activate the environment"
	@echo "  5. python run.py         # Run the profiler (use -h for options)"
	@echo ""
	@echo "Note: The pre-built images (python-base, wrk, databases) are REQUIRED"
	@echo "for the profiler to work correctly. Always run 'make all' first."