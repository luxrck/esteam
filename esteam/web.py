import re
import os
import asyncio

from sanic import Sanic
from sanic.response import html, json, redirect
from sanic_session import InMemorySessionInterface

from aiosteam import SteamClient, EMsg, EResult

from jinja2 import Environment, FileSystemLoader

from .config import config
from .farmer import FarmerManager
from . import otp


__all__ = ["serve"]


app = Sanic(__name__)
session_interface = InMemorySessionInterface()


def init(app, loop):
    app.env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")))
    app.manager = FarmerManager()
    loop.create_task(app.manager.run(async=True))
    app.bot = SteamClient(config().username, config().password, loop=loop)


@app.middleware('request')
async def add_session(request):
    await session_interface.open(request)
    request["session"].setdefault("authorized", False)
    request["session"].setdefault("remain_attemps", config().maxretry)
@app.middleware('response')
async def save_session(request, response):
    print("--->:", response.body)
    await session_interface.save(request, response)


def render_template(tmpl, **kw):
    template = app.env.get_template(tmpl)
    return html(template.render(**kw))


@app.route('/', methods=["GET"])
async def index(request):
    if request["session"]["remain_attemps"] <= 0:
        return render_template("403", text = "Too many wrong attempts in 24 hours.")
    if not request["session"]["authorized"]:
        if app.bot and app.bot.logged_on:
            return render_template("403", text = "Another user is logging or already logged on.")
        return render_template("login")
    return render_template("index", is_farming=(app.bot.username in app.manager.farmers))


# @app.route('/auth', methods=["POST"])
# async def auth(request):
#     session = request["session"]
#     token = request.json.get("token", "")
#     if session["remain_attemps"] <= 0:
#         return json({"errno": 3, "msg": "no more retry."})
#     if not otp.auth(token):
#         if len(token) == 6:
#             session["remain_attemps"] -= 1
#         return json({"errno": 2, "msg": "invalid otp token."})
#     session["authorized"] = True
#     return json({"errno": 0, "msg": "", "success": True})


@app.route('/login', methods=["POST"])
async def login(request):
    session = request["session"]
    token = request.json.get("token", "")
    bot   = app.bot
    if not bot.logged_on:
        r = await bot.login(auth_code=token)
        if r.body.eresult != EResult.OK:
            return json({"errno": 13, "eresult": r.body.eresult, "msg": "login failed: %s" % str(r.msg)})
    session["authorized"] = True
    return json({"errno": 0, "msg": ""})


@app.route("/logout", methods=["POST"])
async def logout(request):
    if not request["session"]["authorized"]:
        return json({"errno": 10, "msg": "method need authorized."})
    del request["session"]["authorized"]
    del request["session"]["remain_attemps"]
    app.manager.pop(app.bot)
    await app.bot.logout()
    return json({"errno": 0, "msg": ""})
    # return redirect("/")


# @app.route('/bots', methods=["GET"])
# async def bots(request):
#     if request.method == "GET":
#         if not request["session"]["authorized"]:
#             return json({"bots": []})
#         return json({
#             "bots": [{
#                 "username": i.username,
#                 "steamid": i.steamid,
#                 "farming": i.username in manager.farmers,
#                 } for i in config.bots.values()
#             ]})


@app.route('/farm', methods=["POST"])
async def farm(request):
    if not request["session"]["authorized"]:
        return json({"errno": 10, "msg": "method need authorized."})
    # username = request.json.get("username", None)
    # if not username:
    #     return json({"errno": 11, "msg": "need specify bot name."})
    # if not username in config.bots:
    #     return json({"errno": 12, "msg": "username not in bots list, please add it first."})
    bot = app.bot
    appids = request.json.get("appids", [])
    scheduler = request.json.get("scheduler", "simple")
    cmd = request.json.get("cmd", "start")
    if cmd == "start":
        app.manager.add(bot, appids, scheduler)
    else:
        app.manager.pop(bot)
    return json({"errno": 0, "msg": ""})


@app.route('/redeem', methods=["POST"])
async def redeem(request):
    result = {"errno": 0, "msg": "", "failed": []}
    for key in request.json.get("keys", "").strip().split("\n"):
        key = re.search("[\w\d]{5}-[\w\d]{5}-[\w\d]{5}", key)
        if not key: continue
        key = key[0]
        resp = await app.bot.register_key(key)
        if resp.body.eresult != EResult.OK:
            result["failed"].append(key)
    return json(result)


def serve(host, port):
    app.run(host=host, port=port, workers=1, before_start=init)


if __name__ == '__main__':
    Config("config.yml")
    app.run(debug=True, workers=1, before_start=init)
