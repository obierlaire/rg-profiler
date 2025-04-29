FROM alpine:latest

# Install dependencies
RUN apk add --no-cache \
    build-base \
    git \
    openssl-dev \
    zlib-dev \
    perl \
    linux-headers

# Clone and build WRK
WORKDIR /tmp
RUN git clone https://github.com/wg/wrk.git && \
    cd wrk && \
    make && \
    cp wrk /usr/local/bin && \
    cd / && \
    rm -rf /tmp/wrk

# Install Lua for scripting
RUN apk add --no-cache lua5.1 lua5.1-dev

# Create directory for scripts
WORKDIR /scripts

# Create scripts directory - will be mounted as a volume at runtime
RUN mkdir -p /scripts

ENTRYPOINT ["wrk"]
