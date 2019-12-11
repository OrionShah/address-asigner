FROM python:3.7-slim

RUN mkdir /app

COPY Pipfile /app
COPY Pipfile.lock /app
WORKDIR /app

RUN pip install --no-cache-dir --disable-pip-version-check pip==18.0 && \
    pip install --no-cache-dir --disable-pip-version-check pipenv==2018.11.14 setuptools==40.0.0 && \
    pipenv install --system --deploy

COPY . /app

RUN mkdir /app/cache

EXPOSE "8000"
