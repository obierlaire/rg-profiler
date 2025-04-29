FROM postgres:latest

# Copy initialization scripts
COPY ./init.sql /docker-entrypoint-initdb.d/

# Set healthcheck
HEALTHCHECK --interval=5s --timeout=5s --retries=10 CMD pg_isready -U benchmarkdbuser -d hello_world

EXPOSE 5432