FROM python:3.10

COPY ./requirements.txt .

RUN set -x

RUN pip install -r requirements.txt

RUN mkdir -p /apps

WORKDIR /apps

COPY . .

EXPOSE 5000