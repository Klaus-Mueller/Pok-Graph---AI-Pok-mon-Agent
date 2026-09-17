"""Collect a bounded Bulbapedia seed; no database writes or embeddings.

Run from the repository root with Python 3.10+: python data/corpora/red-green-blue-first-battle/collect.py
Add --fetch to refresh the three public pages (five seconds between requests).
This is an exploratory section extractor, not the production RAG chunker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CACHE = ROOT / ".pokegraph-cache/bulbapedia-red-green"
BASE = "https://bulbapedia.bulbagarden.net"
SOURCES = {
    "red-green": BASE + "/wiki/Pok%C3%A9mon_Red_and_Green_Versions",
    "blue-teams": BASE + "/wiki/Blue_(game)/Red,_Green,_and_Blue",
    "oak-lab": BASE + "/wiki/Professor_Oak%27s_Laboratory",
}
BATTLES = (
    (1, "First_battle", "first", "first battle"),
    (2, "Second_battle_(optional)", "second-optional", "second battle (optional)"),
    (3, "Third_battle", "third", "third battle"),
    (4, "Fourth_battle", "fourth", "fourth battle"),
    (5, "Fifth_battle", "fifth", "fifth battle"),
    (6, "Sixth_battle", "sixth", "sixth battle"),
    (7, "Seventh_battle", "seventh", "seventh battle"),
    (8, "Eighth_battle_(Champion)", "eighth-champion", "eighth battle (Champion)"),
)
AGENT = "PokeGraph research corpus (manual seed collection)"
LICENSE = "https://creativecommons.org/licenses/by-nc-sa/2.5/"


class Text(HTMLParser):
    """Remove markup and known hidden template fields, retaining party contents."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        hidden = bool(self.stack and self.stack[-1][1])
        hidden |= tag in {"script", "style", "sup"}
        hidden |= "display:none" in attrs.get("style", "").replace(" ", "")
        hidden |= "PKMNnone" in attrs.get("class", "").split()
        if tag not in {"img", "br", "hr", "input", "meta", "link", "wbr", "source"}:
            self.stack.append((tag, hidden))
        if not hidden and tag in {"div", "p", "br", "tr", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        if tag in {"div", "p", "tr", "li"}:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.stack or not self.stack[-1][1]:
            self.parts.append(data)


def plain(html):
    parser = Text()
    parser.feed(html)
    return "\n".join(
        line for raw in "".join(parser.parts).splitlines()
        if (line := " ".join(raw.split()))
    )


def section(html, anchor):
    # The last heading otherwise extends into categories and the site footer.
    footer = re.search(r'<div\b[^>]*class="printfooter"', html)
    if footer:
        html = html[:footer.start()]
    headings = list(re.finditer(r"<h([2-6])\b[^>]*>.*?</h\1>", html, re.S))
    for i, match in enumerate(headings):
        if f'id="{anchor}"' in match.group():
            end = next((h.start() for h in headings[i + 1:] if h[1] <= match[1]), len(html))
            return html[match.end():end]
    raise ValueError(f"Missing section: {anchor}")


def fetch():
    CACHE.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(BASE + "/robots.txt", headers={"User-Agent": AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        robots_text = response.read().decode()
    robots = urllib.robotparser.RobotFileParser()
    robots.parse(robots_text.splitlines())
    delay = max(5, robots.crawl_delay(AGENT) or 0)
    records = []
    for name, url in SOURCES.items():
        if not robots.can_fetch(AGENT, url):
            raise RuntimeError(f"robots.txt disallows {url}")
        time.sleep(delay)
        request = urllib.request.Request(url, headers={"User-Agent": AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read()
            if response.status != 200 or b"wgRevisionId" not in raw:
                raise RuntimeError(f"Unexpected article response: {url}")
            (CACHE / f"{name}.html").write_bytes(raw)
            records.append({"id": name, "url": response.url,
                            "retrieved_at": datetime.now(timezone.utc).isoformat(),
                            "sha256": hashlib.sha256(raw).hexdigest()})
    (CACHE / "fetch.json").write_text(json.dumps(records, indent=2) + "\n")


def build():
    records = json.loads((CACHE / "fetch.json").read_text())
    docs = {}
    for record in records:
        raw = (CACHE / (record["id"] + ".html")).read_bytes()
        if hashlib.sha256(raw).hexdigest() != record["sha256"]:
            raise ValueError("Snapshot hash mismatch")
        html = raw.decode("utf-8")
        revision = re.search(r'"wgRevisionId":(\d+)', html)
        if not revision or f'rel="license" href="{LICENSE}"' not in html:
            raise ValueError("Review source revision/license before proceeding")
        record.update(source_revision=revision[1], license_url=LICENSE,
                      attribution="Bulbapedia contributors", language="en")
        docs[record["id"]] = html

    chunks = []

    def add(identifier, source, anchor, text, **context):
        meta = next(r for r in records if r["id"] == source)
        context.pop("locator", None)
        context.pop("source_game_scope", None)
        context.pop("battle", None)
        chunks.append({"id": identifier,
                       "source_url": meta["url"] + "#" + anchor,
                       "language": "en", "game_scope": ["red-jp", "green-jp"],
                       "generation": 1,
                       "text": text,
                       **context})

    plot = re.findall(r"<p\b[^>]*>.*?</p>", section(docs["red-green"], "Plot"), re.S)
    plot = [p for p in plot if "Spoiler" not in plain(p)]
    add("rg-start", "red-green", "Plot", plain(plot[0]), locator="Plot: first narrative paragraph (includes starter selection)")
    for order, anchor, battle_id, battle_name in BATTLES:
        battle = plain(section(docs["blue-teams"], anchor))
        variants = re.split(r"(?=If the player chose (?:Bulbasaur|Charmander|Squirtle):)", battle)
        if len(variants) != 4:
            raise ValueError(f"Expected three starter variants for {anchor}; review source")
        preamble = variants[0].strip()
        if preamble:
            context_id = "blue-first-outcome" if order == 1 else f"blue-{battle_id}-context"
            add(context_id, "blue-teams", anchor, preamble,
                battle=f"blue-{battle_id}", battle_order=order, battle_name=battle_name,
                locator=f"{anchor}: battle context before starter variants")
        for starter, text in zip(["bulbasaur", "charmander", "squirtle"], variants[1:]):
            if "Lv." not in text or "Status" in text or "Effort levels" in text:
                raise ValueError(f"Unexpected battle template for {anchor}; review source")
            add(f"blue-{battle_id}-{starter}", "blue-teams", anchor, text.strip(),
                battle=f"blue-{battle_id}", battle_order=order, battle_name=battle_name,
                player_starter=starter,
                locator=f"{anchor}: party variant, player chose {starter}",
                source_game_scope="Red, Green, and Japanese Blue; pilot restricts to Red/Green")
    trainers = section(docs["oak-lab"], "Trainers")
    intro = re.search(r"<p\b[^>]*>.*?</p>", trainers, re.S)
    if not intro:
        raise ValueError("Missing laboratory trainer introduction")
    add("oak-first-location", "oak-lab", "Trainers", plain(intro.group()),
        locator="Trainers: introductory paragraph", battle="oak-lab-first")
    (OUT / "sources.json").write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    (OUT / "chunks.jsonl").write_text("".join(json.dumps(c, ensure_ascii=False) + "\n" for c in chunks))
    print(f"Built {len(chunks)} chunks from {len(records)} source snapshots")


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--fetch", action="store_true")
    if args.parse_args().fetch:
        fetch()
    build()
