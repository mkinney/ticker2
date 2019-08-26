import asyncio
import logging
import os

import httpx
import praw
import uvicorn

from aiocache import cached, Cache
from pyppeteer import launch
from starlette.applications import Starlette
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

app = Starlette(debug=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
client = httpx.AsyncClient()
logger = logging.getLogger()
reddit = praw.Reddit(user_agent="EFT - v1.0.0")
subreddit = reddit.subreddit(os.getenv("subreddit"))
templates = Jinja2Templates(directory="templates")


async def generate_and_upload_images(refresh_interval):
    while True:
        args = ["--no-sandbox", "--disable-setuid-sandbox"]
        browser = await launch(headless=True, args=args)
        page = await browser.newPage()
        await page.goto("http://localhost")
        await page.setViewport({"height": 800, "width": 1680})
        clip1 = {"x": 0, "y": 0, "height": 19, "width": 1680}
        clip2 = {"x": 0, "y": 19, "height": 19, "width": 1680}
        await page.screenshot({"path": "output/upper-ticker.png", "clip": clip1})
        await page.screenshot({"path": "output/lower-ticker.png", "clip": clip2})
        await browser.close()
        subreddit.stylesheet.upload("upper-ticker", "output/upper-ticker.png")
        subreddit.stylesheet.upload("lower-ticker", "output/lower-ticker.png")
        logger.info("Ticker image generated & uploaded, check output above.")
        await asyncio.sleep(refresh_interval)


app.add_event_handler("startup", asyncio.create_task(generate_and_upload_images(300)))


async def get_fx():
    logger.info("Fetching live FX")
    url = f"https://openexchangerates.org/api/latest.json?app_id={os.getenv('oer')}"
    resp = await client.get(url)
    if resp.status_code != 200:
        raise Exception(f"FX HTTP {resp.status_code}")
    return resp.json()["rates"]


async def get_omc():
    logger.info("Fetching live OMC")
    resp = await client.get("http://api.openmarketcap.com/api/v1/tokens?size=300")
    if resp.status_code != 200:
        raise Exception(f"OMC HTTP {resp.status_code}")
    logger.info(f"Total records: {resp.json()['records_total']}")
    return {item["global_id"]: item for item in resp.json()["data"]}


@cached(ttl=297, cache=Cache.MEMORY, key="get_data", namespace="main")
async def get_data():
    fx_data = await get_fx()
    omc_data = await get_omc()
    return {
        "vol": "%.2fM" % (float(omc_data["eth"]["volume_usd"]) / 1000000),
        "supply": "%.2fM" % (float(omc_data["eth"]["available_supply"]) / 1000000),
        "fiat": {
            "usd": "$%.2f" % (float(omc_data["eth"]["price_usd"])),
            "gbp": "£%.2f" % (float(omc_data["eth"]["price_usd"]) * fx_data["GBP"]),
            "eur": "€%.2f" % (float(omc_data["eth"]["price_usd"]) * fx_data["EUR"]),
            "cny": "¥%.2f" % (float(omc_data["eth"]["price_usd"]) * fx_data["CNY"]),
            "cad": "$%.2f" % (float(omc_data["eth"]["price_usd"]) * fx_data["CAD"]),
            "aud": "£%.2f" % (float(omc_data["eth"]["price_usd"]) * fx_data["AUD"]),
            "rub": "₽%.2f" % (float(omc_data["eth"]["price_usd"]) * fx_data["RUB"]),
        },
        "erc20": {
            "ant": "%.2f" % (float(omc_data["ant"]["price_usd"])),
            "bat": "%.2f" % (float(omc_data["bat_1"]["price_usd"])),
            "dai": "%.2f" % (float(omc_data["dai"]["price_usd"])),
            "gno": "%.2f" % (float(omc_data["gno"]["price_usd"])),
            "gnt": "%.2f" % (float(omc_data["gnt"]["price_usd"])),
            "link": "%.2f" % (float(omc_data["link"]["price_usd"])),
            "loom": "%.2f" % (float(omc_data["loom"]["price_usd"])),
            "mkr": "%.2f" % (float(omc_data["mkr"]["price_usd"])),
            "omg": "%.2f" % (float(omc_data["omg"]["price_usd"])),
            "poa": "%.2f" % (float(omc_data["poa"]["price_usd"])),
            "rep": "%.2f" % (float(omc_data["rep"]["price_usd"])),
            "storj": "%.2f" % (float(omc_data["storj"]["price_usd"])),
            "snt": "%.2f" % (float(omc_data["snt"]["price_usd"])),
            "zrx": "%.2f" % (float(omc_data["zrx"]["price_usd"])),
        },
    }


@app.route("/")
async def index(request):
    data = await get_data()
    return templates.TemplateResponse("index.html", {"request": request, "data": data})
