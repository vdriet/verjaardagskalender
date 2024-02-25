FROM python:3.12

RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

ENV TZ=Europe/Amsterdam

COPY requirements.txt /usr/src/app/
RUN pip install --upgrade pip
RUN pip --trusted-host pypi.python.org install --no-cache-dir -r requirements.txt

COPY /*.py /usr/src/app/
COPY /templates/* /usr/src/app/templates/

CMD [ "python", "-u", "." ]
