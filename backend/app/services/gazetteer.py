"""Offline India gazetteer from GeoNames (CC-BY 4.0): ~560k towns/villages + 155k post offices with pincodes, in the `places` table.
A place lookup is one indexed query (a few ms), no network, so villages, talukas and pincodes resolve instantly.
It also gives Devanagari spellings of mandi / district / state names (`dev_name`). Nominatim stays as the online fallback.
Load once: docker compose run --rm backend python scripts/load_gazetteer.py /data/raw/geonames"""
import csv
import re
import sys
from functools import lru_cache
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.db import database
from app.models import NameTranslation, Place

DEVA = re.compile(r"[ऀ-ॿ]")
FILLER = {"village", "vill", "taluka", "tal", "tehsil", "district", "dist", "state", "india", "near", "post", "po", "my", "farm", "is", "in", "at",
          "गाँव", "गांव", "गाव", "तालुका", "तहसील", "ज़िला", "जिला", "जिल्हा", "राज्य", "भारत", "के", "पास", "मेरा", "खेत", "माझे", "शेत", "आहे", "है", "में"}
PIN = re.compile(r"(?<!\d)(\d{6})(?!\d)")
ADM_CODES = {"ADM1", "ADM2", "ADM3"}
csv.field_size_limit(sys.maxsize)


def _dev(alts: str) -> str | None:
    return next((a for a in alts.split(",") if DEVA.search(a)), None) if alts else None


def rows(folder: str | Path):
    """Yield place dicts from GeoNames IN.txt (+ admin code files) and postal/IN.txt."""
    folder = Path(folder)
    a1 = {r[0]: r[1] for r in csv.reader(open(folder / "admin1CodesASCII.txt", encoding="utf-8"), delimiter="\t")}
    a2 = {r[0]: r[1] for r in csv.reader(open(folder / "admin2Codes.txt", encoding="utf-8"), delimiter="\t")}
    for r in csv.reader(open(folder / "IN.txt", encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
        if r[8] != "IN" or not (r[6] == "P" or (r[6] == "A" and r[7] in ADM_CODES)):
            continue
        name, dev = r[1], _dev(r[3])
        base = {"name": name, "name_dev": dev, "admin1": a1.get(f"IN.{r[10]}", ""), "admin2": a2.get(f"IN.{r[10]}.{r[11]}", ""),
                "lat": float(r[4]), "lon": float(r[5]), "population": int(r[14] or 0), "kind": "A" if r[6] == "A" else "P"}
        keys = {name.lower(), r[2].lower()} | ({dev} if dev else set())
        if r[6] == "A":  # "Nashik District" is also searchable as "Nashik"
            keys |= {re.sub(r"\s+(district|division|taluka|tahsil|tehsil|subdivision)$", "", k, flags=re.I) for k in list(keys)}
        for k in keys:
            if k and len(k) <= 160:
                yield {"key": k, **base}
    postal = folder / "postal" / "IN.txt"
    if postal.exists():
        for r in csv.reader(open(postal, encoding="utf-8"), delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(r) < 11 or not r[9]:
                continue
            base = {"name": r[2], "name_dev": None, "admin1": r[3], "admin2": r[5], "lat": float(r[9]), "lon": float(r[10]), "population": 0, "kind": "PIN"}
            yield {"key": r[1], **base}
            yield {"key": r[2].lower(), **base}


def load(db: Session, folder: str | Path) -> int:
    """Replace the gazetteer. Postgres uses COPY (about a minute for ~1M rows); other databases insert in batches."""
    db.execute(text("DELETE FROM places"))
    cols = ["key", "name", "name_dev", "admin1", "admin2", "lat", "lon", "population", "kind"]
    n = 0
    if db.bind.dialect.name == "postgresql":
        raw = db.connection().connection.driver_connection
        with raw.cursor().copy(f"COPY places ({', '.join(cols)}) FROM STDIN") as cp:
            for r in rows(folder):
                cp.write_row([r[c] for c in cols])
                n += 1
    else:
        batch = []
        for r in rows(folder):
            batch.append(r)
            if len(batch) == 5000:
                db.execute(Place.__table__.insert(), batch)
                n, batch = n + len(batch), []
        if batch:
            db.execute(Place.__table__.insert(), batch)
            n += len(batch)
    db.commit()
    clear()
    return n


def clear():
    _dev_map.cache_clear()


def _variants(name: str) -> list[str]:
    """Marathi/Hindi oblique forms: पुण्याजवळ -> पुणे, नाशिकला -> नाशिक, नाशिकमध्ये -> नाशिक."""
    out = [name]
    if not name.isascii():
        for suf, rep in (("्याजवळ", "े"), ("जवळ", ""), ("्याला", "े"), ("्यात", "े"), ("्या", "े"), ("मध्ये", ""), ("में", ""), ("ला", ""), ("त", "")):
            if name.endswith(suf) and len(name) > len(suf) + 1:
                out.append(name[: -len(suf)] + rep)
    return out


_C = dict(zip("कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळ",
              "k kh g gh n ch chh j jh n t th d dh n t th d dh n p ph b bh m y r l v sh sh s h l".split()))
_M = {"ा": "a", "ि": "i", "ी": "i", "ु": "u", "ू": "u", "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au", "ॅ": "e", "ॉ": "o"}
_V = {"अ": "a", "आ": "a", "इ": "i", "ई": "i", "उ": "u", "ऊ": "u", "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au"}


def romanize(word: str, schwa: bool = True) -> str:
    """निफाड -> niphad, पिंपळगाव -> pimpalgav: rough, only to search English keys. Standard schwa deletion (V C a C V, right to left)."""
    out = []
    for w in word.replace("़", "").split():
        u = []  # [consonant, vowel, nasal]; vowel None = inherent a, "" = halant
        for ch in w:
            if ch in _C:
                u.append([_C[ch], None, ""])
            elif ch in _M and u:
                u[-1][1] = _M[ch]
            elif ch == "्" and u:
                u[-1][1] = ""
            elif ch in _V:
                u.append(["", _V[ch], ""])
            elif ch in "ंँ" and u:
                u[-1][2] = "n"
        if u and u[-1][1] is None and u[-1][0]:
            u[-1][1] = ""  # final schwa dropped
        for i in range(len(u) - 2, 0, -1) if schwa else ():
            if u[i][1] is None and not u[i][2] and u[i - 1][1] != "" and u[i + 1][1] != "" and u[i + 1][0]:
                u[i][1] = ""
        s = ""
        for i, (c, v, n) in enumerate(u):
            nxt = u[i + 1][0] if i + 1 < len(u) else ""
            s += c + ("a" if v is None else v) + (("m" if nxt[:1] in ("p", "b", "m") else "n") if n else "")
        out.append(s)
    return " ".join(out)


def _latin_variants(word: str) -> list[str]:
    out = {romanize(word), romanize(word, schwa=False)}
    for a, b in (("gav", "gaon"), ("v", "w"), ("ph", "f"), ("au", "o"), ("sh", "s"), ("i", "ee"), ("e", "ee")):
        out |= {x.replace(a, b) for x in out if a in x}
    return sorted(out)[:40]


def find(db: Session, query: str, fuzzy: bool = False) -> dict | None:
    """'Ponda, North Goa' | 'Niphad Nashik' | 'निफाड' | '422303' -> {name, lat, lon, district, state, status}; None if unknown.
    fuzzy=True also tries romanized spellings of Devanagari input (offline last resort; may pick a namesake)."""
    q = (query or "").strip()
    if not q or len(q) > 200:
        return None
    pin = PIN.search(q)
    if pin:
        r = db.execute(select(Place).where(Place.key == pin.group(1)).limit(1)).scalar_one_or_none()
        return _hit(r, f"{r.name} ({pin.group(1)})") if r else None
    clean = " ".join(w for w in re.sub(r"([,/])", r"  ", q.lower().replace(".", " ")).split() if w not in FILLER)
    parts = [p.strip() for p in re.split(r"[,/]", clean) if p.strip()]
    if not parts:
        return None
    words = parts[0].split()
    # longest leading phrase that is a known place; the words after it (and later comma parts) are district/state hints
    for n in range(len(words), 0, -1):
        hints = words[n:] + parts[1:]
        keys = _variants(" ".join(words[:n]))
        if fuzzy:
            keys = [k for v in keys if not v.isascii() for k in _latin_variants(v)]
        r = _best(db, keys, hints)
        if r:  # show the place itself ("Pune", "पुणे"), not the whole sentence the farmer said
            own = r.name if q.isascii() else (r.name_dev or " ".join(words[:n]))
            short = len(q) <= 30 and not ({w.lower() for w in q.replace(",", " ").split()} & FILLER)
            return _hit(r, q if short else own)
    return None


def _best(db, keys, hints):
    cands = db.execute(select(Place).where(Place.key.in_(keys)).order_by(Place.population.desc()).limit(200)).scalars().all() if keys else []
    if not cands:
        return None
    hint = [w for w in " ".join(hints).lower().split() if len(w) > 2]

    def score(p):
        adm = f"{p.admin1} {p.admin2}".lower()
        return (sum(w in adm for w in hint), p.kind == "P" and p.population > 0, p.population, p.kind != "PIN")  # a town beats a district centroid
    return max(cands, key=score)


def _hit(p: Place, name: str) -> dict:
    return {"name": name.strip(" .,!?"), "lat": p.lat, "lon": p.lon, "status": "approximate", "district": p.admin2, "state": p.admin1, "source": "geonames",
            "population": p.population}


@lru_cache(maxsize=1)
def _dev_map() -> dict[str, str]:
    """English (lowercase) -> Devanagari: the most populous GeoNames place of that name, then cached transliterations."""
    m: dict[str, str] = {}
    try:
        with database.SessionLocal() as s:
            for k, dev in s.execute(select(Place.key, Place.name_dev).where(Place.name_dev.isnot(None), Place.kind != "PIN")
                                    .order_by(Place.population.asc())):
                if k.isascii():
                    m[k] = dev  # ascending population: the biggest place of a name wins
            for src, dev in s.execute(select(NameTranslation.src, NameTranslation.dev)):
                m.setdefault(src, dev)
    except Exception:  # no gazetteer loaded yet: names stay in English
        pass
    return m


STATES = {"maharashtra": "महाराष्ट्र", "gujarat": "गुजरात", "karnataka": "कर्नाटक", "madhya pradesh": "मध्य प्रदेश", "uttar pradesh": "उत्तर प्रदेश",
          "rajasthan": "राजस्थान", "punjab": "पंजाब", "haryana": "हरियाणा", "bihar": "बिहार", "west bengal": "पश्चिम बंगाल", "odisha": "ओडिशा",
          "telangana": "तेलंगाना", "andhra pradesh": "आंध्र प्रदेश", "tamil nadu": "तमिलनाडु", "kerala": "केरल", "goa": "गोवा", "assam": "असम",
          "chattisgarh": "छत्तीसगढ़", "chhattisgarh": "छत्तीसगढ़", "jharkhand": "झारखंड", "uttarakhand": "उत्तराखंड", "uttrakhand": "उत्तराखंड",
          "himachal pradesh": "हिमाचल प्रदेश", "jammu and kashmir": "जम्मू और कश्मीर", "nct of delhi": "दिल्ली", "delhi": "दिल्ली", "tripura": "त्रिपुरा",
          "manipur": "मणिपुर", "meghalaya": "मेघालय", "nagaland": "नागालैंड", "mizoram": "मिज़ोरम", "sikkim": "सिक्किम", "chandigarh": "चंडीगढ़",
          "puducherry": "पुदुच्चेरी", "pondicherry": "पुदुच्चेरी", "arunachal pradesh": "अरुणाचल प्रदेश", "andaman and nicobar": "अंडमान और निकोबार"}
WORDS = {"apmc": "APMC", "mandi": "मंडी", "market": "बाज़ार", "yard": "यार्ड", "sub": "उप", "city": "शहर", "rural": "ग्रामीण", "urban": "शहरी",
         "north": "उत्तर", "south": "दक्षिण", "east": "पूर्व", "west": "पश्चिम", "new": "नया", "old": "पुराना"}


def dev_word(w: str) -> str | None:
    lw = w.lower().strip()
    return STATES.get(lw) or WORDS.get(lw) or _dev_map().get(lw)


def dev_name(name: str) -> str:
    """'Lasalgaon(Vinchur), Nashik, Maharashtra' -> 'लासलगाँव(विंचूर), नाशिक, महाराष्ट्र'. Unknown pieces keep the government spelling."""
    if not name or DEVA.search(name):
        return name

    def piece(m):
        seg = m.group(0)
        core = seg.strip()
        if not core:
            return seg
        whole = dev_word(core)
        out = whole or re.sub(r"[A-Za-z][A-Za-z.]*", lambda w: dev_word(w.group(0)) or w.group(0), core)
        return seg.replace(core, out)
    return re.sub(r"[^,()]+", piece, name)


def missing_words(db: Session) -> list[str]:
    """Words of mandi / district names that still have no Devanagari spelling (transliterated once with the local LLM)."""
    from app.models import Mandi
    out = set()
    for n, d in db.execute(select(Mandi.name, Mandi.district)):
        for w in re.findall(r"[A-Za-z][A-Za-z.]+", f"{n} {d}"):
            if w.upper() != "APMC" and not dev_word(w) and not re.fullmatch(r"[A-Z.]{1,4}", w):
                out.add(w.lower())
    return sorted(out)


def count(db: Session) -> int:
    return db.scalar(select(func.count(Place.id))) or 0
