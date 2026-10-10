FROM python:3.12.1-alpine3.19

ADD requirements.txt /app/requirements.txt
ADD constraints.txt /app/constraints.txt

ENV PIP_CONSTRAINT=/app/constraints.txt

# If set to true the Django database migrations needs be run externally 
ENV EXTERNAL_MIGRATION=false

RUN set -ex \
    && apk add --no-cache --virtual .build-deps postgresql-dev build-base gcc musl-dev jpeg-dev zlib-dev libffi-dev cairo-dev pango-dev gdk-pixbuf-dev mariadb-dev python3-dev \
    && python -m venv /env \
    && /env/bin/pip install --upgrade pip \
    && /env/bin/pip install --no-cache-dir -r /app/requirements.txt \
    && runDeps="$(scanelf --needed --nobanner --recursive /env \
    | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
    | sort -u \
    | xargs -r apk info --installed \
    | sort -u)" \
    && apk add --virtual rundeps $runDeps \
    && apk del .build-deps
RUN apk add --no-cache curl ca-certificates

# Add AWS RDS eu-central-1 CA bundle
ADD https://truststore.pki.rds.amazonaws.com/eu-central-1/eu-central-1-bundle.pem /etc/ssl/certs/rds-ca-bundle.pem
RUN chmod 644 /etc/ssl/certs/rds-ca-bundle.pem

# LICENSE and NOTICE come from the repository root (build context "repo").
COPY --from=repo LICENSE NOTICE /usr/share/libreseal/

RUN addgroup -S app && adduser -S app -G app
ADD . /app
WORKDIR /app
RUN chmod 555 /app/scripts/*
RUN chown -R app:app /app
USER app

ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH

# OCI metadata; version and revision are set by the release workflow.
ARG LIBRESEAL_VERSION=dev
ARG LIBRESEAL_REVISION=unknown
LABEL org.opencontainers.image.title="libreseal-backend" \
      org.opencontainers.image.description="LibreSeal backend (Django API and worker). Independent fork of Phase Console; not affiliated with or endorsed by Phase / Phi Security Inc." \
      org.opencontainers.image.source="https://github.com/Dos2Locos/libreseal" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.version="${LIBRESEAL_VERSION}" \
      org.opencontainers.image.revision="${LIBRESEAL_REVISION}"

EXPOSE 8000
CMD ["/app/scripts/start.sh"]
