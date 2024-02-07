FROM alpine:3.14
RUN apk add --no-cache python3
RUN python3 -m pip install --upgrade pip && python3 -m pip install requests pyserial -y
COPY data/main.py ./main.py

ENTRYPOINT ["python3","main.py"]