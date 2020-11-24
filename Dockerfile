FROM python:3.6
ENV PYTHONUNBUFFERED 1
RUN mkdir /opt/scancode.io/
WORKDIR /opt/scancode.io/
COPY etc/requirements/base.txt /opt/scancode.io/
RUN pip install -r base.txt
COPY . /opt/scancode.io/
RUN pip install .
