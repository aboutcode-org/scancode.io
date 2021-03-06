FROM python:3.9
ENV PYTHONUNBUFFERED 1
RUN mkdir /opt/scancodeio/
RUN mkdir -p /var/scancodeio/static/
RUN mkdir -p /var/scancodeio/workspace/
WORKDIR /opt/scancodeio/
COPY etc/requirements/base.txt /opt/scancodeio/
RUN pip install -r base.txt
COPY . /opt/scancodeio/
RUN pip install .
