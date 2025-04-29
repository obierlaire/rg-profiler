FROM mysql:latest

# Copy initialization scripts
COPY ./init.sql /docker-entrypoint-initdb.d/

# Configure MySQL for better performance
COPY ./my.cnf /etc/mysql/conf.d/

# Set healthcheck
HEALTHCHECK --interval=5s --timeout=5s --retries=10 CMD mysqladmin ping -h localhost -u benchmarkdbuser -pbenchmarkdbpass

EXPOSE 3306