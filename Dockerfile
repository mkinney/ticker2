FROM tiangolo/uvicorn-gunicorn-starlette:python3.7
RUN apt-get update -y && apt-get install -y libasound2 libatk-bridge2.0-0 libgtk-3-0 libnss3 libxtst-dev xvfb
COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
RUN pyppeteer-install
COPY ./app /app