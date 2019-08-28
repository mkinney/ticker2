import asyncio
import logging
import os

import httpx
import praw

from aiocache import cached, Cache
from pyppeteer import launch
from starlette.applications import Starlette
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

app = Starlette(debug=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
chrome_path = "/usr/bin/chromium-browser"
client = httpx.AsyncClient()
log = logging.getLogger()
reddit = praw.Reddit(user_agent="EFT - v1.0.0")
sub = reddit.subreddit(os.getenv("subreddit"))
templates = Jinja2Templates(directory="templates")


async def generate_and_upload_images(refresh_interval=300):
    while True:  # TODO: only generate images if any price changed since last update
        args = ["--no-sandbox", "--disable-setuid-sandbox"]
        browser = await launch(args=args, headless=True, executablePath=chrome_path)
        page = await browser.newPage()
        resp = await page.goto("http://localhost")
        await page.setViewport({"height": 800, "width": 1680})
        clip1 = {"x": 0, "y": 0, "height": 19, "width": 1680}
        clip2 = {"x": 0, "y": 19, "height": 19, "width": 1680}
        if resp.status != 200:
            log.warn(f'Error, ticker not generated. Wait {refresh_interval} seconds')
            await asyncio.sleep(refresh_interval)
            continue
        for name, clip in [("upper-ticker", clip1), ("lower-ticker", clip2)]:
            await page.screenshot(
                {"path": f"out/{name}.png", "clip": clip, "omitBackground": True}
            )
            log.info(f"Generated {name}, uploading to Reddit.")
            log.info(sub.stylesheet.upload(name, f"out/{name}.png"))  # TODO: blocks
        await browser.close()
        await asyncio.sleep(refresh_interval)


async def get_fx():
    log.info("Fetching live FX")
    url = f"https://openexchangerates.org/api/latest.json?app_id={os.getenv('oer')}"
    resp = await client.get(url)
    if resp.status_code != 200:
        log.warn(f"FX HTTP {resp.status_code}")
        return {}
    return resp.json()["rates"]


async def get_omc(num=300):
    log.info("Fetching live OMC")
    resp = await client.get(f"http://api.openmarketcap.com/api/v1/tokens?size={num}")
    if resp.status_code != 200 or resp.json()['records_total'] == 0:
        log.warn(f"OMC HTTP {resp.status_code} {resp.json()['records_total']}")
        return {}
    return {item["global_id"]: item for item in resp.json()["data"]}


@cached(ttl=297, cache=Cache.MEMORY, key="get_data", namespace="main")
async def get_data():
    fx = await get_fx()
    omc = await get_omc()
    fiat = os.getenv("fiat").split(",")
    erc20 = os.getenv("erc20").split(",")
    try:
        eth = omc["eth"]
    except KeyError:
        logging.warn(f"OMC data failure: {omc}")
        return None
    data = {
        "vol": "%.2fM" % (float(eth["volume_usd"]) / 1000000),
        "supply": "%.2fM" % (float(eth["available_supply"]) / 1000000),
        "fiat": {f: "%.2f" % (float(eth["price_usd"]) * fx[f.upper()]) for f in fiat},
        "erc20": {e: "%.2f" % (float(omc[e]["price_usd"])) for e in erc20},
    }
    data["erc20"]["bat"] = data["erc20"].pop("bat_1")
    log.info(data)
    return data


@app.route("/")
async def index(request):
    data = await get_data()
    if not data:
        return HTMLResponse(content="<body></body", status_code=424)
    return templates.TemplateResponse("index.html", {"request": request, "data": data})


asyncio.create_task(generate_and_upload_images())
