FROM nginx
RUN apt-get update && \
    apt-get install -y openssl && \
    mkdir -p /etc/nginx/ssl && \
    openssl ecparam -genkey -name secp384r1 | openssl ec -out /etc/nginx/ssl/nginx.key && \
    openssl req -new -x509 -sha256 -key /etc/nginx/ssl/nginx.key -out /etc/nginx/ssl/nginx.crt -days 365 \
        -subj "/C=SG/ST=Wordwideweb/L=The Cloud/CN=example.com"

COPY nginx/real-ip.sh /docker-entrypoint.d/40-libreseal-real-ip.sh
RUN chmod 0755 /docker-entrypoint.d/40-libreseal-real-ip.sh
