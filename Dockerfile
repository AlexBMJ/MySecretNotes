FROM python:3.10-alpine

RUN apk update && apk add curl wget netcat-openbsd nmap

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
EXPOSE 9000

CMD [ "python", "app.py" ]
