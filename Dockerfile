FROM alpine:edge
RUN apk add --no-cache chromium nss freetype freetype-dev harfbuzz ttf-freefont msttcorefonts-installer fontconfig python3 && \
    update-ms-fonts && \
    fc-cache -f
RUN apk add --no-cache --virtual .build-deps gcc python3-dev musl-dev alpine-sdk
COPY ./requirements.txt /requirements.txt
RUN pip3 install --upgrade pip && pip3 install -r requirements.txt && apk del .build-deps
COPY ./app /app
WORKDIR /app
EXPOSE 80
ENTRYPOINT uvicorn main:app --host 0.0.0.0 --port 80