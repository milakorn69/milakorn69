#!/usr/bin/env python3
"""Render media/status.svg for the profile README from mrs-ml.website/data/lava.json.

Standard library only. Run locally or from the GitHub Action:

    python scripts/build_status.py            # fetch the live file
    python scripts/build_status.py lava.json  # or render from a saved copy
"""
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

SOURCE = "https://mrs-ml.website/data/lava.json"
OUT = Path(__file__).resolve().parent.parent / "media" / "status.svg"

# spec id -> (network, label); same grouping as the site
FAM = {
    "AVAX": ("avalanche", "Mainnet"), "AVALANCHEC": ("avalanche", "C-Chain"), "AVALANCHEP": ("avalanche", "P-Chain"), "AVAXT": ("avalanche", "Testnet"),
    "AXELAR": ("axelar", "Mainnet"), "AXELART": ("axelar", "Testnet"),
    "BCH": ("bitcoincash", "Mainnet"), "BCHT": ("bitcoincash", "Testnet"),
    "BTC": ("bitcoin", "Mainnet"), "BTCT": ("bitcoin", "Testnet"),
    "CARDANO": ("cardano", "Mainnet"), "CARDANOT": ("cardano", "Preprod"),
    "CASPER": ("casper", "Mainnet"), "CASPERT": ("casper", "Testnet"),
    "COSMOSHUB": ("cosmos", "Mainnet"), "COSMOSHUBT": ("cosmos", "Testnet"),
    "ETH1": ("ethereum", "Mainnet"), "SEP1": ("ethereum", "Sepolia"),
    "FTM250": ("fantom", "Mainnet"),
    "HYPERLIQUID": ("hyperliquid", "Mainnet"), "HYPERLIQUIDT": ("hyperliquid", "Testnet"),
    "IOTA": ("iota", "Mainnet"), "IOTAT": ("iota", "Testnet"),
    "LAVA": ("lava", "Mainnet"),
    "NEAR": ("near", "Mainnet"), "NEART": ("near", "Testnet"),
    "OPTM": ("optimism", "Mainnet"), "OPTMS": ("optimism", "Sepolia"),
    "POLKADOTASSETHUB": ("polkadot", "Asset Hub"), "POLKADOTASSETHUBT": ("polkadot", "Westend"),
    "POLYGON": ("polygon", "Mainnet"), "POLYGONA": ("polygon", "Amoy"),
    "SONIC": ("sonic", "Mainnet"),
    "STRK": ("starknet", "Mainnet"), "STRKS": ("starknet", "Sepolia"),
    "TEZOS": ("tezos", "Mainnet"), "TEZOST": ("tezos", "Shadownet"),
    "TRX": ("tron", "Mainnet"),
    "XLM": ("stellar", "Mainnet"), "XLMT": ("stellar", "Testnet"),
}
NAMES = {
    "lava": "Lava", "ethereum": "Ethereum", "bitcoin": "Bitcoin", "bitcoincash": "Bitcoin Cash",
    "hyperliquid": "Hyperliquid", "fantom": "Fantom", "iota": "IOTA", "polkadot": "Polkadot",
    "polygon": "Polygon", "axelar": "Axelar", "avalanche": "Avalanche", "starknet": "Starknet",
    "stellar": "Stellar", "cosmos": "Cosmos Hub", "casper": "Casper", "tezos": "Tezos",
    "cardano": "Cardano", "near": "NEAR", "tron": "Tron", "optimism": "Optimism", "sonic": "Sonic",
}

# palette from mrs-ml.website
BG, SURFACE, LINE = "#0A0908", "#131110", "#2A2420"
TEXT, MUTED, FAINT = "#EFEAE3", "#A39B90", "#6F685F"
GOLD, GOLD_BRIGHT = "#D69A52", "#EDBA7C"
OK, WARN, BAD = "#3CCB4E", "#F5B544", "#FF5C5C"
SANS = "'Geist','Segoe UI',Helvetica,Arial,sans-serif"
MONO = "'Geist Mono',ui-monospace,Consolas,Menlo,monospace"
W = 880


def short(n):
    for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= div:
            v = n / div
            return f"{v:.2f}{suf}" if v < 10 else f"{v:.1f}{suf}" if v < 100 else f"{v:.0f}{suf}"
    return str(int(n))


def text(x, y, s, size=13, fill=TEXT, weight=400, anchor="start", font=SANS, spacing=None):
    sp = f' letter-spacing="{spacing}"' if spacing else ""
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}"{sp}>{escape(str(s))}</text>')


def render(d):
    services = d.get("services", [])
    healthy = sum(1 for s in services if s.get("status") == "healthy")
    lat = [s["latencyMs"] for s in services if s.get("status") == "healthy" and s.get("latencyMs")]
    avg = round(sum(lat) / len(lat)) if lat else None
    updated = datetime.strptime(d["updated"], "%Y-%m-%dT%H:%M:%SZ")

    # group services by network, keep the site's order by relays
    fams = {}
    for s in services:
        fam, label = FAM.get(s["id"], (s["id"].lower(), s["id"]))
        f = fams.setdefault(fam, {"name": NAMES.get(fam, s.get("name", fam)), "items": [], "relays": 0})
        f["items"].append((label, s.get("status") == "healthy"))
        f["relays"] += s.get("relays30d") or 0
    fams = sorted(fams.values(), key=lambda f: -f["relays"])

    out = []
    y = 0

    # status line
    all_ok = healthy == len(services)
    dot = OK if all_ok else WARN if healthy >= len(services) * 0.8 else BAD
    msg = "All systems operational" if all_ok else f"{healthy} of {len(services)} services healthy"
    line = f"{msg} · {len(services)} services" + (f" · avg {avg} ms" if avg else "")
    out.append(f'<circle cx="34" cy="38" r="5" fill="{dot}"/><circle cx="34" cy="38" r="9" fill="{dot}" opacity=".18"/>')
    out.append(text(50, 43, line, 14, TEXT, 500))
    out.append(text(W - 28, 43, "updated " + updated.strftime("%d %b %Y %H:%M") + " UTC", 11, FAINT, anchor="end", font=MONO))
    y = 68
    out.append(f'<line x1="28" y1="{y}" x2="{W - 28}" y2="{y}" stroke="{LINE}"/>')

    # metrics strip
    metrics = [
        ("RELAYS · 30 DAYS", short(d.get("relays30d", 0)), "served through Lava"),
        ("RELAYS · ALL TIME", short(d.get("relaysTotal", 0)), "since 2023"),
        ("COMPUTE UNITS · 30D", short(d.get("cu30d", 0)), "billed on chain"),
        ("SERVICES HEALTHY", f"{healthy}/{len(services)}", f"{len(fams)} networks"),
    ]
    cw = (W - 56) / 4
    for i, (k, v, s) in enumerate(metrics):
        x = 28 + i * cw + (0 if i == 0 else 20)
        if i:
            out.append(f'<line x1="{28 + i * cw}" y1="{y + 16}" x2="{28 + i * cw}" y2="{y + 94}" stroke="{LINE}"/>')
        out.append(text(x, y + 36, k, 10.5, MUTED, 500, spacing="1.2"))
        out.append(text(x, y + 72, v, 30, GOLD_BRIGHT if i == 0 else TEXT, 600, spacing="-0.5"))
        out.append(text(x, y + 92, s, 12, MUTED))
    y += 110
    out.append(f'<line x1="28" y1="{y}" x2="{W - 28}" y2="{y}" stroke="{LINE}"/>')

    # top networks by all-time relays
    top = d.get("topChains", [])[:5]
    if top:
        y += 34
        out.append(text(28, y, "WHERE THE TRAFFIC GOES · SHARE OF ALL-TIME RELAYS", 10.5, GOLD, 500, spacing="1.4"))
        y += 14
        mx = max(t["share"] for t in top) or 1
        bar_x, bar_w = 168, W - 28 - 168 - 120
        for t in top:
            y += 26
            fam = FAM.get(t["chain"], (t["chain"].lower(), ""))[0]
            out.append(text(28, y, NAMES.get(fam, t["chain"]) + ("" if FAM.get(t["chain"], ("", "Mainnet"))[1] in ("Mainnet", "") else " " + FAM[t["chain"]][1]), 13, TEXT))
            out.append(f'<rect x="{bar_x}" y="{y - 9}" width="{bar_w}" height="6" rx="3" fill="{SURFACE}"/>')
            out.append(f'<rect x="{bar_x}" y="{y - 9}" width="{max(4, t["share"] / mx * bar_w):.1f}" height="6" rx="3" fill="url(#gold)"/>')
            out.append(text(W - 28, y, f'{t["share"]:.1f}%  ·  {short(t["relays"])}', 12, MUTED, anchor="end", font=MONO))
        y += 26
        out.append(f'<line x1="28" y1="{y}" x2="{W - 28}" y2="{y}" stroke="{LINE}"/>')

    # network grid
    y += 34
    out.append(text(28, y, f"NETWORKS · {len(services)} SERVICES", 10.5, GOLD, 500, spacing="1.4"))
    y += 16
    cols, gap = 3, 12
    cell_w = (W - 56 - gap * (cols - 1)) / cols
    cell_h = 50
    for i, f in enumerate(fams):
        cx = 28 + (i % cols) * (cell_w + gap)
        cy = y + (i // cols) * (cell_h + gap)
        ok_all = all(h for _, h in f["items"])
        out.append(f'<rect x="{cx:.1f}" y="{cy}" width="{cell_w:.1f}" height="{cell_h}" rx="10" fill="{SURFACE}" stroke="{"#3A2E22" if ok_all else "#5A2A2A"}"/>')
        out.append(text(cx + 14, cy + 21, f["name"], 13.5, TEXT, 600))
        out.append(text(cx + cell_w - 14, cy + 21, short(f["relays"]) + " / 30d" if f["relays"] else "—", 10.5, MUTED, anchor="end", font=MONO))
        lx = cx + 14
        for label, h in f["items"]:
            out.append(f'<circle cx="{lx + 3}" cy="{cy + 35}" r="3" fill="{OK if h else BAD}"/>')
            out.append(text(lx + 10, cy + 39, label, 10.5, MUTED if h else BAD))
            lx += 16 + len(label) * 5.9
    rows = (len(fams) + cols - 1) // cols
    y += rows * (cell_h + gap) - gap + 30

    out.append(text(28, y, "Live data from mrs-ml.website · relays and CU as reported by Lava", 11, FAINT))
    H = y + 24

    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
            f'aria-label="MrsML Lava provider status: {escape(msg)}, {len(services)} services">'
            f'<defs><linearGradient id="gold" x1="0" x2="1"><stop offset="0" stop-color="#B87333"/><stop offset="1" stop-color="{GOLD_BRIGHT}"/></linearGradient>'
            f'<linearGradient id="edge" x1="0" x2="1"><stop offset="0" stop-color="{GOLD}" stop-opacity="0"/><stop offset=".5" stop-color="{GOLD}"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></linearGradient></defs>'
            f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="16" fill="{BG}" stroke="#3A2E22"/>'
            f'<rect x="{W * .2}" y="0" width="{W * .6}" height="1" fill="url(#edge)"/>'
            + "".join(out) + "</svg>")


def main():
    if len(sys.argv) > 1:
        data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    else:
        req = urllib.request.Request(SOURCE, headers={"User-Agent": "milakorn69-status-card"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(data), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
