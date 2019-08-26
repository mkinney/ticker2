Ticker2
=======

This is a much simpler version of the ticker script, it does however use HTML to render the images which is a lot less efficient but much more configurable. It gathers all required data in a maximum of 2 API calls (often 1 call as FX data can be cached)

Setup
-----

```sh
cp .env.example .env
```

You need to set all of the variables e.g. reddit tokens, openexchangerate token, subreddit to target etc.

Building (option 1)
-------------------

```sh
docker build -t ethfinance/ticker2 .
```

Pulling (option 2)
------------------

```sh
docker pull ethfinance/ticker2
```

Developing
----------

```sh
docker run -d --env-file .env --name ticker2 -v $(pwd)/app:/app -p 80:80 ethfinance/ticker2 /start-reload.sh
```

Running
-------

```sh
docker run -d --env-file .env --name ticker2 -p 80:80 ethfinance/ticker2
```

You can optionally mount the output volume so you can see what is going on, run this command instead:

```sh
docker run -d -v /full/path/to/output/dir:/app/output/ --env-file .env --name ticker2 -p 80:80 ethfinance/ticker2
```
