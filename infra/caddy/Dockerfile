# syntax=docker/dockerfile:1
# Caddy with the DuckDNS DNS provider compiled in, for DNS-01 wildcard certs.
FROM caddy:2-builder AS build
RUN xcaddy build \
    --with github.com/caddy-dns/duckdns

FROM caddy:2
COPY --from=build /usr/bin/caddy /usr/bin/caddy
