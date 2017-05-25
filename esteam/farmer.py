import re
import json
import logging
import queue
import threading
from importlib import import_module
import asyncio

from lxml import etree


class Farmer(object):
    def __init__(self, steam, appids=[], scheduler="simple"):
        self._state = "running"
        self.mutex = threading.RLock()
        self.steam = steam
        async def sched(self, appids=[], scheduler="simple"):
            games, __scheduler__ = {}, None
            while True:
                if self.state == "pause":
                    if self.steam.client.current_games_played:
                        await self.steam.clear()
                    yield True; continue
                if self.state == "stop":
                    return
                if not games:
                    games = await self.farmable()
                    if appids: games = { i:games[i] for i in appids }
                    module = import_module('esteam.schedulers.' + scheduler)
                    __scheduler__ = module.scheduler(games, self.steam)
                r = await __scheduler__.__anext__()
                if not r: return
                yield r
        self.sched = sched(self, appids, scheduler)

    async def _games_farmable(self):
        session = await self.steam.session()
        if not session: return {}
        def parse_page(doc):
            games = doc.xpath("//div[contains(@class, 'badge_row') and contains(@class, 'is_link')]")
            results = {}
            for game in games:
                try:
                    link = game.xpath("a[contains(@class, 'badge_row_overlay')]/@href")[0].strip()
                    appid = re.findall("gamecards/(\d+)", link)
                    if not appid: continue
                    appid = int(appid[0])
                    progress = game.xpath(".//div[contains(@class, 'badge_title_stats_drops')]/span[contains(@class, 'progress_info_bold')]/text()")
                    if not progress: continue
                    progress = progress[0].strip()
                    cards = re.findall("\d+", progress)
                    if not cards: continue
                    cards = int(cards[0])
                    results[appid] = {'cards_remain': cards}
                except Exception as e:
                    continue
            return results
        url_template = "http://steamcommunity.com/id/luxrck/badges/?p={}"
        url = url_template.format(1)

        r = await session.get(url)
        htmldoc = await r.text()

        doc = etree.HTML(htmldoc)
        num_pages = doc.xpath("//div[contains(@class, 'profile_paging')]/div[contains(@class, 'pageLinks')]")
        if num_pages:
            num_pages = num_pages[0].xpath("a[contains(@class, 'pagelink')]/text()")
            if num_pages:
                num_pages = re.search("\d+", num_pages[-1].strip())
                if num_pages: num_pages = int(num_pages)
        else:
            num_pages = 1
        results = {}
        results.update(parse_page(doc))
        for p in range(2, num_pages+1):
            url = url_template.format(p)
            htmldoc = session.get(url).text
            doc = etree.HTML(htmldoc)
            results.update(parse_page(doc))
        return results

    async def farmable(self):
        owned_games = await self.steam.games()
        games = await self._games_farmable()
        for game in games:
            info = owned_games.get(game, {})
            games[game].update(info)
        return games

    @property
    def state(self):
        return self._state
    @state.setter
    def state(self, val):
        self.mutex.acquire()
        self._state = val
        self.mutex.release()


class FarmerManager(object):
    __instance__ = None
    def __new__(cls, *args, **kwargs):
        if not FarmerManager.__instance__:
            FarmerManager.__instance__ = object.__new__(cls)
            FarmerManager.__init__(FarmerManager.__instance__, *args, **kwargs)
        return FarmerManager.__instance__

    def __init__(self, loop=None):
        self.farmers = {}
        self._addq = queue.Queue()
        self._popq = queue.Queue()
        self._state = "running"  # running, pause, stop
        self.mutex = threading.RLock()
        self.loop = loop or asyncio.get_event_loop()

    @property
    def state(self):
        return self._state
    @state.setter
    def state(self, val):
        self.mutex.acquire()
        self._state = val
        self.mutex.release()

    def add(self, steam, appids=[], scheduler="simple"):
        f = Farmer(steam, appids, scheduler=scheduler)
        self._addq.put(f)
        # self.farmers[steam.username] = f

    def pop(self, steam):
        self._popq.put(steam)
        # return self.farmers.pop(steam.username, None)

    async def run_async(self):
        while True:
            if self.state == "pause":
                await asyncio.sleep(1); continue
            if self.state == "stop":
                return
            for u,f in self.farmers.items():
                r = await f.sched.__anext__()
                if not r: self.farmers.pop(u)
            while not self._addq.empty():
                try:
                    f = self._addq.get_nowait()
                    self.farmers.setdefault(f.steam.username, f)
                except queue.Empty:
                    break
            while not self._popq.empty():
                try:
                    s = self._popq.get_nowait()
                    await s.games_played([])
                    self.farmers.pop(s.username, None)
                except queue.Empty:
                    break
            await asyncio.sleep(1)


    def run(self, asynchronous=False):
        if not asynchronous:
            return threading.Thread(target=self.loop.run_until_complete, args=([__run__(self)]), daemon=True).start()
        return self.run_async()
