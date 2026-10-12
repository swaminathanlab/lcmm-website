"""Generate the site's Markdown pages from data/*.yaml and content/*.md.

Writes into docs/ (generated files are git-ignored), then `zensical build` makes the site.
    python scripts/build_pages.py && zensical serve
"""
from __future__ import annotations

import html
import re
import shutil
from datetime import date
from pathlib import Path

import markdown as md
import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"
CONTENT = ROOT / "content"
PARTIALS = ROOT / "overrides" / "partials"


def load(name: str):
    return yaml.safe_load((DATA / name).read_text(encoding="utf-8"))


def e(s) -> str:
    return html.escape(str(s or ""), quote=True)


def inline(text: str) -> str:
    """Markdown -> HTML without the wrapping <p>."""
    out = md.markdown(str(text or "").strip())
    return re.sub(r"^<p>(.*)</p>$", r"\1", out, flags=re.S)


def block(text: str) -> str:
    return md.markdown(str(text or "").strip())


def write(rel: str, front: dict, body: str) -> None:
    path = DOCS / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = yaml.safe_dump(front, allow_unicode=True, sort_keys=False).strip()
    path.write_text(f"---\n{fm}\n---\n\n{body.strip()}\n", encoding="utf-8")


def initials(name: str) -> str:
    parts = [p for p in re.split(r"[\s-]+", name) if p]
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


# ---------------------------------------------------------------- publications

def publications() -> list[dict]:
    pubs = load("publications.yaml") or []
    ov = load("publications_overrides.yaml") or {}
    hide = {str(h).lower() for h in ov.get("hide") or []}
    fixes = {str(k).lower(): v for k, v in (ov.get("fix") or {}).items()}
    out = []
    for p in pubs + list(ov.get("add") or []):
        ids = {str(p.get("pmid") or ""), str(p.get("doi") or "").lower()} - {""}
        if ids & hide or p.get("retracted"):   # retracted papers are never listed
            continue
        for i in ids:
            p = {**p, **fixes.get(i, {})}
        out.append(p)
    out.sort(key=lambda p: (-int(p["year"]), p["title"].lower()))
    return out


def find_pub(pubs: list[dict], ref) -> dict | None:
    ref = str(ref).lower()
    return next((p for p in pubs if ref in (str(p.get("pmid")), str(p.get("doi", "")).lower())), None)


def lab_names(people: dict) -> set[str]:
    names = set()
    for group in ("pi", "members", "alumni"):
        for m in people.get(group) or []:
            if m.get("pubmed_name"):
                names.add(m["pubmed_name"].lower())
    return names


def is_lab(author: str, names: set[str]) -> bool:
    a = author.lower()
    # "Swaminathan VS" matches "Swaminathan V"
    return any(a == n or (a.startswith(n) and a[len(n):].isalpha()) for n in names)


def authors_html(authors: list[str], names: set[str], limit: int = 12) -> str:
    shown = authors if len(authors) <= limit else authors[: limit - 2] + ["…"] + authors[-1:]
    if len(authors) > limit:
        # keep lab members visible even in long author lists
        extra = [a for a in authors[limit - 2 : -1] if is_lab(a, names)]
        if extra:
            shown = authors[: limit - 2] + ["…"] + extra + ["…"] + authors[-1:]
    return ", ".join(f"<strong>{e(a)}</strong>" if is_lab(a, names) else e(a) for a in shown)


def pub_html(p: dict, names: set[str], compact: bool = False) -> str:
    badges = []
    if p.get("preprint"):
        badges.append('<span class="badge badge--preprint">Preprint</span>')
    if p.get("kind") == "review":
        badges.append('<span class="badge">Review / comment</span>')
    if p.get("retracted"):
        badges.append('<span class="badge badge--retracted">Retracted</span>')
    links = []
    if p.get("doi"):
        links.append(f'<a href="https://doi.org/{e(p["doi"])}">DOI</a>')
    if p.get("pmid"):
        links.append(f'<a href="https://pubmed.ncbi.nlm.nih.gov/{e(p["pmid"])}/">PubMed</a>')
    title_url = f"https://doi.org/{p['doi']}" if p.get("doi") else (f"https://pubmed.ncbi.nlm.nih.gov/{p['pmid']}/" if p.get("pmid") else "")
    title = f'<a href="{e(title_url)}">{e(p["title"])}</a>' if title_url else e(p["title"])
    search = e(" ".join([p["title"], " ".join(p.get("authors", [])), p.get("journal", ""), str(p["year"])]).lower())
    parts = [
        f'<li class="pub{" pub--retracted" if p.get("retracted") else ""}" data-search="{search}">',
        f'<div class="pub__title">{title} {" ".join(badges)}</div>',
    ]
    if not compact:
        parts.append(f'<div class="pub__authors">{authors_html(p.get("authors", []), names)}</div>')
    parts.append(
        f'<div class="pub__meta"><em>{e(p.get("journal"))}</em> {e(p["year"])}'
        + (f' · {" · ".join(links)}' if links and not compact else "")
        + "</div></li>"
    )
    return "".join(parts)



# ---------------------------------------------------------------- media (gallery folder)

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
VIDEO_EXT = {".mp4", ".webm"}
GALLERY_SRC = DATA / "gallery"
MEDIA_OUT = DOCS / "assets" / "gallery"
CACHE = ROOT / ".cache" / "gallery"


def _resized(src: Path, width: int, tag: str) -> str:
    """Web-sized JPEG copy of src (cached by size+mtime); returns its file name."""
    from PIL import Image, ImageOps

    st = src.stat()
    name = f"{src.stem}-{tag}-{int(st.st_mtime)}-{st.st_size}.jpg"
    cached = CACHE / name
    if not cached.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            if im.mode != "RGB":
                im = im.convert("RGB")
            if im.width > width:
                im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
            im.save(cached, "JPEG", quality=85, optimize=True, progressive=True)
    MEDIA_OUT.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(cached, MEDIA_OUT / name)
    return name


def gallery_files() -> dict[str, Path]:
    if not GALLERY_SRC.exists():
        return {}
    return {f.name: f for f in sorted(GALLERY_SRC.glob("*")) if f.suffix.lower() in IMAGE_EXT | VIDEO_EXT}


_media_cache: dict[str, dict] = {}


def media(name: str) -> dict | None:
    """Web-ready version of data/gallery/<name>: {'video': ...} or {'thumb': ..., 'full': ...}."""
    if not name:
        return None
    if name in _media_cache:
        return _media_cache[name]
    src = gallery_files().get(name)
    if not src:
        print(f"warning: {name} is not in data/gallery/")
        return None
    if src.suffix.lower() in VIDEO_EXT:
        MEDIA_OUT.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, MEDIA_OUT / src.name)
        out = {"video": src.name}
    else:
        out = {"thumb": _resized(src, 900, "t"), "full": _resized(src, 2400, "f")}
    _media_cache[name] = out
    return out


def media_tag(m: dict, prefix: str, cls: str = "", alt: str = "", full: bool = False) -> str:
    if m.get("video"):
        return f'<video class="{cls}" src="{prefix}assets/gallery/{e(m["video"])}" autoplay muted loop playsinline preload="metadata"></video>'
    return f'<img class="{cls}" src="{prefix}assets/gallery/{e(m["full" if full else "thumb"])}" alt="{e(alt)}" loading="lazy">'


def gallery_items() -> tuple[dict, list[dict]]:
    cfg = load("gallery.yaml") or {}
    files = gallery_files()
    listed = [i for i in cfg.get("items") or [] if i.get("file")]
    for i in listed:
        if i["file"] not in files:
            print(f"warning: data/gallery.yaml lists {i['file']}, which is not in data/gallery/")
    order = [i for i in listed if i["file"] in files]
    seen = {i["file"] for i in listed}
    order += [{"file": n} for n in files if n not in seen]
    return cfg, [{**i, **media(i["file"])} for i in order if not i.get("hide")]


def gallery_html(items: list[dict], prefix: str) -> str:
    figs = []
    for it in items:
        cap = " · ".join(x for x in (it.get("caption"), f"Credit: {it['credit']}" if it.get("credit") else "") if x)
        capdiv = f'<figcaption class="gallery__cap">{e(cap)}</figcaption>' if cap else ""
        full = f"{prefix}assets/gallery/{e(it.get('video') or it['full'])}"
        kind = "video" if it.get("video") else "image"
        figs.append(
            f'<figure class="gallery__item" tabindex="0" data-full="{full}" data-kind="{kind}" data-caption="{e(cap)}">'
            f'{media_tag(it, prefix, alt=it.get("caption") or "")}{capdiv}</figure>'
        )
    return f'<div class="gallery">{"".join(figs)}</div>'


# ---------------------------------------------------------------- shared bits

def accent(text: str) -> str:
    """'How we *work*' -> 'How we <em>work</em>' (escaped)."""
    return re.sub(r"\*(.+?)\*", r"<em>\1</em>", e(text))


def section_head(eyebrow: str, title: str, center: bool = True) -> str:
    return (
        f'<div class="lc-head{" lc-head--center" if center else ""}"><p class="lc-eyebrow">{e(eyebrow)}</p>'
        f'<h2 class="lc-title">{accent(title)}</h2></div>'
    )


def page_head(eyebrow: str, title: str, lede: str = "") -> str:
    lede_html = f'<div class="lc-pagehead__lede">{block(lede)}</div>' if lede else ""
    return (
        f'<header class="lc-pagehead" markdown="0"><p class="lc-eyebrow">{e(eyebrow)}</p>'
        f'<h1>{accent(title)}</h1>{lede_html}</header>'
    )


def tags_html(tags) -> str:
    return "".join(f'<span class="lc-tag">{e(t)}</span>' for t in tags or [])


def theme_card(t: dict, i: int, prefix: str, link: bool) -> str:
    m = media(t.get("media") or "")
    visual = media_tag(m, prefix, "lc-card__media", t["title"]) if m else f'<div class="lc-card__media lc-card__media--pattern lc-pattern-{i % 3}"></div>'
    first = block(t["summary"])
    title = f'<a href="{prefix}research/#{e(t["id"])}">{e(t["title"])}</a>' if link else e(t["title"])
    return (
        f'<article class="lc-card">{visual}<div class="lc-card__body">'
        f'<p class="lc-card__num">{i:02d}</p><h3 class="lc-card__title">{title}</h3>'
        f'<div class="lc-card__text">{first}</div><div class="lc-tags">{tags_html(t.get("tags"))}</div></div></article>'
    )


def photo_for(m: dict, prefix: str) -> str:
    for ext in ("jpg", "jpeg", "png", "webp"):
        src = DATA / "photos" / f"{m.get('id')}.{ext}"
        if m.get("id") and src.exists():
            dst = DOCS / "assets" / "people" / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            return f'<img class="lc-person__photo" src="{prefix}assets/people/{src.name}" alt="{e(m["name"])}" loading="lazy">'
    return f'<div class="lc-person__photo lc-person__photo--initials" aria-hidden="true">{initials(m["name"])}</div>'


LINKS = {
    "orcid": ("ORCID", lambda v: f"https://orcid.org/{v}"),
    "email": ("Email", lambda v: f"mailto:{v}"),
    "scholar": ("Scholar", lambda v: v),
    "bluesky": ("Bluesky", lambda v: f"https://bsky.app/profile/{v}"),
    "github": ("GitHub", lambda v: f"https://github.com/{v}"),
    "linkedin": ("LinkedIn", lambda v: v),
    "website": ("Website", lambda v: v),
}


def person_tile(m: dict, prefix: str) -> str:
    return (
        f'<article class="lc-person">{photo_for(m, prefix)}<h3 class="lc-person__name">{e(m["name"])}</h3>'
        f'<p class="lc-person__role">{e(m["role"])}</p></article>'
    )


def recruit_tile(prefix: str) -> str:
    return (
        f'<a class="lc-person lc-person--recruit" href="{prefix}join-us/"><h3 class="lc-person__name">We are <em>recruiting</em></h3>'
        f'<p>PhD students, postdocs and degree-project students.</p><span class="lc-more">Get in touch →</span></a>'
    )


def contact_block(site: dict) -> str:
    c = site["contact"]
    addr = "<br>".join(e(l) for l in str(c.get("address", "")).strip().splitlines())
    affs = "<br>".join(f'<a href="{e(a["url"])}">{e(a["name"])}</a>' for a in site.get("affiliations") or [])
    rows = [("Email", f'<a href="mailto:{e(c["email"])}">{e(c["email"])}</a>')]
    if c.get("orcid"):
        rows.append(("ORCID", f'<a href="https://orcid.org/{e(c["orcid"])}">{e(c["orcid"])}</a>'))
    for key, label, url in (
        ("bluesky", "Bluesky", "https://bsky.app/profile/{}"),
        ("google_scholar", "Scholar", "{}"),
        ("lund_portal", "Lund portal", "{}"),
        ("github", "GitHub", "https://github.com/{}"),
    ):
        if c.get(key):
            rows.append((label, f'<a href="{e(url.format(c[key]))}">{e(c[key]) if key in ("bluesky", "github") else "Profile"}</a>'))
    rowhtml = "".join(f'<div class="lc-contact__row"><span>{l}</span><span>{v}</span></div>' for l, v in rows)
    return (
        f'<div class="lc-contact"><div><h3 class="lc-contact__name">{e(site["name"])}</h3>'
        f'<p>{affs}</p><p class="lc-muted">{addr}</p></div><div>{rowhtml}</div></div>'
    )


# ---------------------------------------------------------------- pages

def page_home(site, research, pubs, names, news, ov, gcfg, gitems, people) -> None:
    # hero picture: hero_image, else first gallery item
    hero = media(site.get("hero_image") or "") or (gitems[0] if gitems else None)
    hero_vis = media_tag(hero, "", "lc-hero__media", site.get("hero_caption") or "", full=True) if hero else '<div class="lc-hero__media lc-pattern-0"></div>'
    hero_cap = f'<p class="lc-hero__cap">{e(site["hero_caption"])}</p>' if site.get("hero_caption") else ""

    cards = "".join(theme_card(t, i, "", True) for i, t in enumerate(research["themes"], 1))

    n_home = int(gcfg.get("show_on_home", 12))
    gallery = ""
    if gitems:
        more = f'<p class="lc-center"><a class="lc-btn lc-btn--ghost" href="gallery/">All {len(gitems)} images</a></p>' if len(gitems) > n_home else ""
        gallery = (
            f'<section class="lc-section lc-section--wide" id="images">{section_head("Gallery", gcfg.get("title") or "Inside the *lab*")}'
            f'{gallery_html(gitems[:n_home], "")}{more}</section>'
        )

    featured = [p for p in (find_pub(pubs, r) for r in ov.get("featured") or []) if p] or pubs[:6]
    featured.sort(key=lambda p: -int(p["year"]))
    def selpub(p):
        url = f"https://doi.org/{p['doi']}" if p.get("doi") else f"https://pubmed.ncbi.nlm.nih.gov/{p.get('pmid')}/"
        first = p.get("authors", [""])[0]
        return (f'<li class="lc-selpub"><span class="lc-selpub__year">{e(p["year"])}</span>'
                f'<a class="lc-selpub__title" href="{e(url)}">{e(p["title"])}</a>'
                f'<span class="lc-selpub__journal">{e(first)} et al. · <em>{e(p.get("journal"))}</em></span></li>')

    sel = "".join(selpub(p) for p in featured)

    team = [*(people.get("pi") or []), *(people.get("members") or [])]
    tiles = "".join(person_tile(m, "") for m in team) + recruit_tile("")

    news_items = "".join(
        f'<li><time datetime="{e(n["date"])}">{n["date"]:%d %b %Y}</time><span>{inline(n["text"])}</span></li>' for n in news[:3]
    )
    funders = " · ".join(f'<a href="{e(f["url"])}">{e(f["name"])}</a>' if f.get("url") else e(f["name"]) for f in site.get("funding") or [])

    body = f"""
<section class="lc-hero" markdown="0">
  <div class="lc-hero__visual">{hero_vis}{hero_cap}</div>
  <div class="lc-hero__text">
    <p class="lc-eyebrow">{e(site['name'])}</p>
    <h1 class="lc-hero__title">{accent(site.get('headline') or site['name'])}</h1>
    <p class="lc-hero__tagline">{e(site['tagline'])}</p>
    <p class="lc-hero__actions"><a class="lc-btn" href="#research">Our research</a><a class="lc-btn lc-btn--ghost" href="people/">People</a><a class="lc-btn lc-btn--ghost" href="join-us/">Join us</a></p>
  </div>
</section>

<section class="lc-section" id="research" markdown="0">
  {section_head("Research", "What we *study*")}
  <div class="lc-intro">{block(site['intro'])}</div>
  <div class="lc-cards">{cards}</div>
</section>

{gallery}

<section class="lc-section" id="publications" markdown="0">
  {section_head("Publications", "Selected *work*")}
  <ul class="lc-selpubs">{sel}</ul>
  <p class="lc-center"><a class="lc-btn lc-btn--ghost" href="publications/">All publications</a></p>
</section>

<section class="lc-section" id="people" markdown="0">
  {section_head("People", "Who we *are*")}
  <div class="lc-people">{tiles}</div>
  <p class="lc-center"><a class="lc-btn lc-btn--ghost" href="people/">View all bios</a></p>
</section>

<section class="lc-section lc-section--split" markdown="0">
  <div>{section_head("News", "Latest", center=False)}<ul class="lc-news">{news_items}</ul><a class="lc-more" href="news/">All news →</a></div>
  <div>{section_head("Support", "Funding", center=False)}<p class="lc-muted">{funders}</p></div>
</section>

<section class="lc-section" id="contact" markdown="0">
  {section_head("Contact", "Get in *touch*")}
  {contact_block(site)}
</section>
"""
    write("index.md", {"title": site["name"], "hide": ["navigation", "toc"], "template": "home.html"}, body)


def page_research(research, pubs, names) -> None:
    out = [page_head("Research", "What we *study*", research["intro"])]
    for i, t in enumerate(research["themes"], 1):
        papers = [p for p in (find_pub(pubs, r) for r in t.get("papers") or []) if p]
        m = media(t.get("media") or "")
        vis = media_tag(m, "../", "lc-theme__media", t["title"]) if m else f'<div class="lc-theme__media lc-pattern-{i % 3}"></div>'
        plist = (
            f'<p class="lc-eyebrow lc-eyebrow--small">Papers</p><ul class="pubs pubs--compact">{"".join(pub_html(p, names, True) for p in papers)}</ul>'
            if papers else ""
        )
        out.append(
            f'<section class="lc-theme" id="{e(t["id"])}" markdown="0">{vis}<div class="lc-theme__body">'
            f'<p class="lc-card__num">{i:02d}</p><h2>{e(t["title"])}</h2>{block(t["summary"])}'
            f'<div class="lc-tags">{tags_html(t.get("tags"))}</div>{plist}</div></section>'
        )
    write("research.md", {"title": "Research", "hide": ["toc"]}, "\n".join(out))


def page_publications(pubs, names, site) -> None:
    years: dict[int, list] = {}
    for p in pubs:
        years.setdefault(int(p["year"]), []).append(p)
    n_pre = sum(1 for p in pubs if p.get("preprint"))
    head = (
        '<div class="pubtools" markdown="0">'
        '<input type="search" id="pubsearch" placeholder="Filter by title, author, journal or year" aria-label="Filter publications">'
        f'<p class="pubcount"><span id="pubshown">{len(pubs)}</span> of {len(pubs)} listed · '
        f'{len(pubs) - n_pre} published, {n_pre} preprint{"s" if n_pre != 1 else ""}. Lab members in <strong>bold</strong>. '
        f'Full record on <a href="https://orcid.org/{e(site["contact"]["orcid"])}">ORCID</a>.</p></div>'
    )
    blocks = [
        f'<section class="year" markdown="0"><h2 id="y{y}">{y}</h2><ul class="pubs">{"".join(pub_html(p, names) for p in ps)}</ul></section>'
        for y, ps in sorted(years.items(), reverse=True)
    ]
    note = f'<p class="small" markdown="0">Updated weekly from Europe PMC. Last generated {date.today():%d %b %Y}.</p>'
    write("publications.md", {"title": "Publications", "hide": ["toc"]}, page_head("Publications", "Our *work*") + head + "\n".join(blocks) + note)


def person_full(m: dict, big: bool = False) -> str:
    links = m.get("links") or {}
    linkhtml = " · ".join(f'<a href="{e(LINKS[k][1](v))}">{LINKS[k][0]}</a>' for k, v in links.items() if v and k in LINKS)
    extra = f'<div class="lc-bio__text">{block(m["bio"])}</div>' if big and m.get("bio") else (f'<p class="lc-muted">{e(m["blurb"])}</p>' if m.get("blurb") else "")
    if m.get("now"):
        extra += f'<p class="lc-muted">Now: {e(m["now"])}</p>'
    return (
        f'<article class="lc-bio{" lc-bio--pi" if big else ""}">{photo_for(m, "../")}<div>'
        f'<h3 class="lc-person__name">{e(m["name"])}</h3><p class="lc-person__role">{e(m["role"])}</p>'
        f'{extra}{f"<p class=lc-bio__links>{linkhtml}</p>" if linkhtml else ""}</div></article>'
    )


def page_people(people) -> None:
    out = [page_head("People", "Who we *are*"), '<div markdown="0">']
    out += [person_full(m, big=True) for m in people.get("pi") or []]
    out.append('<p class="lc-eyebrow lc-eyebrow--rule">Lab members</p><div class="lc-bios">')
    out += [person_full(m) for m in people.get("members") or []]
    out.append(recruit_tile("../").replace("lc-person lc-person--recruit", "lc-bio lc-person--recruit"))
    out.append("</div>")
    if people.get("alumni"):
        out.append('<p class="lc-eyebrow lc-eyebrow--rule">Alumni</p><div class="lc-bios">')
        out += [person_full(m) for m in people["alumni"]]
        out.append("</div>")
    out.append("</div>")
    write("people.md", {"title": "People", "hide": ["toc"]}, "\n".join(out))


def page_gallery(cfg: dict, items: list[dict]) -> None:
    body = gallery_html(items, "../") if items else "<p>No images yet: add files to <code>data/gallery/</code>.</p>"
    write("gallery.md", {"title": "Gallery", "hide": ["toc"]}, page_head("Gallery", cfg.get("title") or "Inside the *lab*") + f'<div markdown="0">{body}</div>')


def page_news(news) -> None:
    items = "".join(f'<li><time datetime="{e(n["date"])}">{n["date"]:%d %b %Y}</time><span>{inline(n["text"])}</span></li>' for n in news)
    write("news.md", {"title": "News", "hide": ["toc"]}, page_head("News", "Lab *news*") + f'<ul class="lc-news lc-news--page" markdown="0">{items}</ul>')


def page_contact(site) -> None:
    body = page_head("Contact", "Get in *touch*") + f'<div markdown="0">{contact_block(site)}</div>'
    extra = CONTENT / "contact.md"
    if extra.exists():
        body += "\n\n" + extra.read_text(encoding="utf-8")
    write("contact.md", {"title": "Contact", "hide": ["toc"]}, body)


def header_nav() -> None:
    """Top menu from mkdocs.yml `nav` (Home left out: the lab name links home)."""
    cfg = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
    links = []
    for item in cfg.get("nav") or []:
        (title, path), = item.items()
        if path == "index.md":
            continue
        url = path[:-3] + "/" if path.endswith(".md") else path
        cls = "lc-nav__link lc-nav__link--cta" if title.lower() == "join us" else "lc-nav__link"
        links.append(f'<a class="{cls}" href="{{{{ base_url }}}}/{url}" data-path="{url}">{e(title)}</a>')
    PARTIALS.mkdir(parents=True, exist_ok=True)
    (PARTIALS / "lcmm-nav.html").write_text('<nav class="lc-nav" aria-label="Main">' + "".join(links) + "</nav>\n", encoding="utf-8")


def footer(site) -> None:
    PARTIALS.mkdir(parents=True, exist_ok=True)
    affs = " · ".join(e(a["name"].split(",")[0]) for a in site.get("affiliations") or [])
    (PARTIALS / "lcmm-footer.html").write_text(
        f"""<footer class="lc-footer">
  <div class="lc-footer__inner">
    <span class="lc-footer__brand">{e(site['short_name'])}</span>
    <span class="lc-footer__fine">{e(site['name'])} · Lund University · © {date.today().year}</span>
    <span class="lc-footer__links"><a href="mailto:{e(site['contact']['email'])}">Email</a><a href="https://orcid.org/{e(site['contact']['orcid'])}">ORCID</a></span>
  </div>
</footer>
""",
        encoding="utf-8",
    )


def copy_content() -> None:
    """content/*.md -> docs/, with the first '# Title' turned into the styled page header."""
    for f in CONTENT.glob("*.md"):
        if f.name == "contact.md":
            continue
        text = f.read_text(encoding="utf-8")
        m = re.search(r"^# (.+)$", text, flags=re.M)
        if m:
            eyebrow = m.group(1).replace("*", "")
            text = text[: m.start()] + page_head(eyebrow, m.group(1)) + text[m.end():]
        (DOCS / f.name).write_text(text, encoding="utf-8")


def main() -> None:
    site, research, people = load("site.yaml"), load("research.yaml"), load("people.yaml")
    news = sorted(load("news.yaml") or [], key=lambda n: n["date"], reverse=True)
    ov = load("publications_overrides.yaml") or {}
    pubs = publications()
    names = lab_names(people)
    for t in research["themes"]:
        for ref in t.get("papers") or []:
            if not find_pub(pubs, ref):
                print(f"warning: research theme '{t['id']}' lists {ref}, which is not in the publication list")
    gcfg, gitems = gallery_items()
    page_home(site, research, pubs, names, news, ov, gcfg, gitems, people)
    page_research(research, pubs, names)
    page_publications(pubs, names, site)
    page_people(people)
    page_gallery(gcfg, gitems)
    page_news(news)
    page_contact(site)
    copy_content()
    footer(site)
    header_nav()
    print(f"pages written: {len(pubs)} publications, {len(people.get('members') or [])} members, {len(gitems)} gallery items")


if __name__ == "__main__":
    main()
