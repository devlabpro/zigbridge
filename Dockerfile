ARG BUILD_FROM
FROM $BUILD_FROM

RUN \
  apk --no-cache add \
    nginx gcc g++\
  \
  && mkdir -p /run/nginx

COPY ingress.conf /etc/nginx/http.d/


RUN apk add --no-cache python3 py3-pip python3-dev
RUN python3 -m pip install --upgrade pip
COPY data/web.py /web.py
COPY data/db.py /db.py
COPY data/requirements.txt /requirements.txt
RUN python3 -m pip install -r requirements.txt
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
WORKDIR /
#CMD [ "nginx","-g","daemon off;error_log /dev/stdout debug;" ]
ENTRYPOINT ["/entrypoint.sh"]