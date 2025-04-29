FROM mongo:latest

# Copy initialization script
COPY init.js /docker-entrypoint-initdb.d/

# Set healthcheck 
HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
  CMD mongosh --quiet --eval 'db.runCommand("ping").ok' localhost:27017/admin -u benchmarkdbuser -p benchmarkdbpass || exit 1

# Expose standard MongoDB port
EXPOSE 27017