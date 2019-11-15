FROM python:3.6-stretch

#MAINTAINER Debasish "dsahoo@kent.edu"

LABEL "Maintainer"="Debasish Sahoo"

#RUN apt-get update -y && \
    #apt-get install -y python3 python3-pip

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip3 install -r requirements.txt

COPY . /app

#ENTRYPOINT [ "gunicorn" ]

CMD [ "gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "wsgi:app" ]