FROM python:3.6-alpine

RUN pip3 install prometheus_client

WORKDIR /exporter

COPY dovecot_exporter.py .

CMD [ "python", "./dovecot_exporter.py" ]
