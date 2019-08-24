""" ticker2 - provide price information for https://old.reddit.com/r/ethfinance/
"""
import logging
import os

import httpx
import praw

from aiocache import cached, Cache
from pyppeteer import launch
from starlette.applications import Starlette
from starlette.background import BackgroundTask
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates
from starlette.staticfiles import StaticFiles

logger = logging.getLogger()
logger.setLevel(logging.INFO)

templates = Jinja2Templates(directory="templates")

app = Starlette(debug=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
client = httpx.AsyncClient()
reddit = praw.Reddit(user_agent="EFT - v1.0.0")
subreddit = reddit.subreddit(os.getenv('subreddit'))


@app.route("/screenshot")
async def screenshot():
    """ take a screenshot """
    task = BackgroundTask(generate_and_upload_images)
    return JSONResponse({'status': 'ok'}, background=task)


async def generate_and_upload_images():
    """ generate and upload the image """
    browser = await launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox'])
    page = await browser.newPage()
    await page.goto("http://localhost")
    await page.setViewport({'height': 800, 'width': 1680})
    clip1 = {'x':0, 'y':0, 'height':19, 'width':1680}
    clip2 = {'x':0, 'y':19, 'height':19, 'width':1680}
    await page.screenshot({"path": "output/upper-ticker.png", "clip": clip1})
    await page.screenshot({"path": "output/lower-ticker.png", "clip": clip2})
    await browser.close()
    subreddit.stylesheet.upload("upper-ticker-test", "output/upper-ticker.png")
    subreddit.stylesheet.upload("lower-ticker-test", "output/lower-ticker.png")
    logger.info('Ticker image generated and uploaded, check for errors above.')
    return True


async def get_fx():
    """ get the live exchange rates """
    logger.info("Fetching live FX")
    resp = await client.get(
        f"https://openexchangerates.org/api/latest.json?app_id={os.getenv('oer')}"
    )
    if resp.status_code != 200:
        raise Exception(f"FX HTTP {resp.status_code}")
    return resp.json()["rates"]


async def get_omc():
    """ get the latest market prices """
    logger.info("Fetching live OMC")
    resp = await client.get("http://api.openmarketcap.com/api/v1/tokens?size=300")
    if resp.status_code != 200:
        raise Exception(f"OMC HTTP {resp.status_code}")
    logger.info("Total records: %s", resp.json()['records_total'])
    return {item["global_id"]: item for item in resp.json()["data"]}


@cached(ttl=299, cache=Cache.MEMORY, key="get_data", namespace="main")
async def get_data():
    """ process the omc data """
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
            "ant":  "%.2f" % (float(omc_data["ant"]["price_usd"])),
            "bat":  "%.2f" % (float(omc_data["bat_1"]["price_usd"])),
            "dai":  "%.2f" % (float(omc_data["dai"]["price_usd"])),
            "gno":  "%.2f" % (float(omc_data["gno"]["price_usd"])),
            "gnt":  "%.2f" % (float(omc_data["gnt"]["price_usd"])),
            "link": "%.2f" % (float(omc_data["link"]["price_usd"])),
            "loom": "%.2f" % (float(omc_data["loom"]["price_usd"])),
            "mkr":  "%.2f" % (float(omc_data["mkr"]["price_usd"])),
            "omg":  "%.2f" % (float(omc_data["omg"]["price_usd"])),
            "poa":  "%.2f" % (float(omc_data["poa"]["price_usd"])),
            "rep":  "%.2f" % (float(omc_data["rep"]["price_usd"])),
            "storj":"%.2f" % (float(omc_data["storj"]["price_usd"])),
            "snt":  "%.2f" % (float(omc_data["snt"]["price_usd"])),
            "zrx":  "%.2f" % (float(omc_data["zrx"]["price_usd"])),
        },
    }


@app.route("/")
async def index(request):
    """ main route """
    data = await get_data()
    return templates.TemplateResponse("index.html", {"request": request, "data": data})
