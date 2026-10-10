FROM nginx
RUN apt-get update && \
    apt-get install -y openssl && \
    mkdir -p /etc/nginx/ssl && \
    openssl ecparam -genkey -name secp384r1 | openssl ec -out /etc/nginx/ssl/nginx.key && \
    openssl req -new -x509 -sha256 -key /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt -days 365 \
        -subj "/C=SG/ST=Wordwideweb/L=The Cloud/CN=example.com"

COPY nginx/real-ip.sh /docker-entrypoint.d/40-libreseal-real-ip.sh
RUN chmod 0755 /docker-entrypoint.d/40-libreseal-real-ip.sh
COPY LICENSE NOTICE /usr/share/libreseal/

# OCI metadata; version and revision are set by the release workflow.
ARG LIBRESEAL_VERSION=dev
ARG LIBRESEAL_REVISION=unknown
LABEL org.opencontainers.image.title="libreseal-nginx" \
      org.opencontainers.image.description="LibreSeal reverse proxy (nginx). Independent fork of Phase Console; not affiliated with or endorsed by Phase / Phi Security Inc." \
      org.opencontainers.image.source="https://github.com/Dos2Locos/libreseal" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${LIBRESEAL_VERSION}" \
      org.opencontainers.image.revision="${LIBRESEAL_REVISION}"
