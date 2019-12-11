FROM python:3.7-alpine3.8
MAINTAINER Sergey Levitin <selevit@gmail.com>

RUN addgroup -g 10001 app && adduser -u 10001 -D -h /app -G app app

COPY Pipfile /app
COPY Pipfile.lock /app
WORKDIR /app

RUN set -x && \
    apk add --no-cache --update -t .build-deps build-base postgresql-dev libxml2-dev libxslt-dev linux-headers git \
                                               gcc musl-dev libjpeg-turbo-dev zlib-dev libffi-dev && \
    pip install --no-cache-dir --disable-pip-version-check pip==18.0 && \
    pip install --no-cache-dir --disable-pip-version-check pipenv==2018.11.14 setuptools==40.0.0 && \
    pipenv install --system --deploy && \
    runDeps="$( \
      scanelf --needed --nobanner --recursive /usr/local/lib/python3.7 \
        | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
        | sort -u \
        | xargs -r apk info --installed \
        | sort -u \
    )" && \
    apk add --no-cache -t .run-deps $runDeps && \
    apk del .build-deps && \
    apk add bash

COPY . /app

RUN set -x \
    mkdir /app/cache
    chmod -R a+rX /app && \
    chown -R app:app /app

USER app
EXPOSE "8000"
