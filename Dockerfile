FROM python:3.6
ENV PYTHONUNBUFFERED 1
RUN mkdir /code
WORKDIR /code
COPY etc/requirements/base.txt /code/
RUN pip install -r base.txt
COPY . /code/
RUN pip install .
