#!/usr/bin/env python3
"""
WiFi Recon Tool — passive beacon scanner for Windows
Uses netsh (built-in), no admin needed for basic scan.
"""

import subprocess, re, time, sys, os, random, threading, msvcrt
from datetime import datetime

# ── auto-install dependencies ─────────────────────────────────────────────────
for pkg in ("rich", "colorama"):
    try:
        __import__(pkg)
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"],
                       capture_output=True)

from rich.console    import Console
from rich.table      import Table
from rich.panel      import Panel
from rich.text       import Text
from rich.live       import Live
from rich.align      import Align
from rich.rule       import Rule
from rich            import box
from rich.columns    import Columns
from rich.padding    import Padding
import colorama
colorama.init()

console = Console(highlight=False)
W       = console.width or 100

# ─────────────────────────────────────────────────────────────────────────────
# ASCII BANNER
# ─────────────────────────────────────────────────────────────────────────────
BANNER = r"""
 ██╗    ██╗██╗███████╗██╗    ███████╗ ██████╗ █████╗ ███╗  ██╗
 ██║    ██║██║██╔════╝██║    ██╔════╝██╔════╝██╔══██╗████╗ ██║
 ██║ █╗ ██║██║█████╗  ██║    ███████╗██║     ███████║██╔██╗██║
 ██║███╗██║██║██╔══╝  ██║    ╚════██║██║     ██╔══██║██║╚████║
 ╚███╔███╔╝██║██║     ██║    ███████║╚██████╗██║  ██║██║ ╚███║
  ╚══╝╚══╝ ╚═╝╚═╝     ╚═╝    ╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚══╝"""

SUBTITLE = "[ N E T W O R K   R E C O N   T O O L   v 2 . 0 ]"
TAGLINE  = "passive • non-invasive • beacon analysis only"

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR SCHEME  (all rich markup)
# ─────────────────────────────────────────────────────────────────────────────
C_BORDER  = "bright_green"
C_HEAD    = "bold bright_green"
C_DIM     = "dim green"
C_WARN    = "bold yellow"
C_CRIT    = "bold red"
C_INFO    = "cyan"
C_OK      = "green"

# ─────────────────────────────────────────────────────────────────────────────
# KNOWN VENDOR PREFIXES  (OUI first 3 octets)
# ─────────────────────────────────────────────────────────────────────────────
VENDORS = {
    "00:50:f2":"Microsoft","00:1a:11":"Google","b8:27:eb":"Raspberry Pi",
    "dc:a6:32":"Raspberry Pi","00:17:f2":"Apple","00:25:00":"Apple",
    "a4:c3:f0":"Apple","00:26:b9":"Dell","00:21:cc":"Cisco","00:1b:2f":"Asus",
    "00:0c:29":"VMware","00:50:56":"VMware","00:1e:8c":"AsRock",
    "74:d0:2b":"Netgear","a0:21:b7":"Netgear","e8:fc:af":"TP-Link",
    "98:da:c4":"TP-Link","f4:f2:6d":"TP-Link","10:62:eb":"D-Link",
    "00:1c:f0":"D-Link","b8:a3:86":"Linksys","00:14:bf":"Linksys",
    "c4:04:15":"Huawei","00:e0:fc":"Huawei","28:6c:07":"Xiaomi",
    "64:09:80":"Xiaomi","18:31:bf":"Ubiquiti","24:a4:3c":"Ubiquiti",
    "00:0d:97":"ZyXEL",
}

def vendor_lookup(bssid: str) -> str:
    prefix = bssid[:8].lower()
    return VENDORS.get(prefix, "Unknown")

# ─────────────────────────────────────────────────────────────────────────────
# NETSH SCAN  + PARSER
# ─────────────────────────────────────────────────────────────────────────────
def run_scan() -> list[dict]:
    try:
        r = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=10
        )
        return _parse(r.stdout)
    except FileNotFoundError:
        return []
    except Exception:
        return []

def _parse(raw: str) -> list[dict]:
    nets, cur = [], {}
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()

        if re.match(r"^SSID\s*\d*$", k):
            if cur.get("ssid") is not None:
                nets.append(cur)
                cur = {}
            cur["ssid"] = v or "<Hidden SSID>"

        elif "BSSID" in k:
            m = re.search(r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})", v)
            if m:
                cur["bssid"] = m.group(1).upper()

        elif "Authentication" in k:
            cur["auth"] = v
        elif "Encryption" in k:
            cur["enc"] = v
        elif "Signal" in k:
            try:   cur["signal"] = int(v.replace("%",""))
            except: cur["signal"] = 0
        elif "Radio type" in k:
            cur["radio"] = v
        elif "Channel" in k:
            try:   cur["ch"] = int(v)
            except: cur["ch"] = 0
        elif "Network type" in k:
            cur["type"] = v

    if cur.get("ssid") is not None:
        nets.append(cur)
    return nets

# ─────────────────────────────────────────────────────────────────────────────
# SECURITY ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────
def analyse(net: dict) -> dict:
    auth = net.get("auth", "").upper()
    enc  = net.get("enc",  "").upper()

    if "WPA3" in auth:
        grade, color, bar, label = "A+",  C_OK,    "█████", "WPA3-SAE"
        risk = []
    elif "WPA2" in auth and "CCMP" in enc:
        grade, color, bar, label = "A",   C_OK,    "████░", "WPA2-CCMP"
        risk = []
    elif "WPA2" in auth and "TKIP" in enc:
        grade, color, bar, label = "B",   C_WARN,  "███░░", "WPA2-TKIP"
        risk = ["TKIP is deprecated — vulnerable to MICHAEL attack"]
    elif "WPA2" in auth:
        grade, color, bar, label = "B+",  C_OK,    "████░", "WPA2"
        risk = []
    elif "WPA-" in auth or auth == "WPAPSK" or auth.startswith("WPA "):
        grade, color, bar, label = "C",   C_WARN,  "██░░░", "WPA (legacy)"
        risk = ["WPA (v1) is obsolete — upgradeable to WPA2/3"]
    elif "OPEN" in auth or enc in ("NONE",""):
        grade, color, bar, label = "F",   C_CRIT,  "█░░░░", "OPEN / None"
        risk = ["NO encryption — all traffic visible in plaintext",
                "Any device can join this network freely"]
    else:
        grade, color, bar, label = "?",   "dim",   "░░░░░", auth or "Unknown"
        risk = []

    # Extra checks
    sig = net.get("signal", 0)
    ssid = net.get("ssid","")
    if ssid.strip() == "" or ssid == "<Hidden SSID>":
        risk.append("Hidden SSID — not necessarily more secure")
    if sig >= 90:
        risk.append(f"Very strong signal ({sig}%) — likely nearby device")

    return dict(grade=grade, color=color, bar=bar, label=label, risks=risk)

# ─────────────────────────────────────────────────────────────────────────────
# VISUAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def sig_bar(pct: int) -> Text:
    blocks = int(pct / 20)
    filled = "▮" * blocks
    empty  = "▯" * (5 - blocks)
    color  = "bright_green" if pct >= 65 else ("yellow" if pct >= 35 else "red")
    t = Text()
    t.append(filled, style=color)
    t.append(empty,  style="dim")
    t.append(f" {pct:>3}%", style=color)
    return t

def freq_tag(ch: int) -> str:
    if   1  <= ch <= 14:  return "[cyan]2.4GHz[/cyan]"
    elif 36 <= ch <= 177: return "[magenta]5GHz[/magenta]"
    else:                 return "[dim]?[/dim]"

def glitch(text: str) -> str:
    """Randomly corrupt a few chars for the intro glitch effect."""
    chars = list(text)
    glitch_chars = "!@#$%^&*<>?|\\░▒▓█"
    for _ in range(max(1, len(chars)//10)):
        i = random.randint(0, len(chars)-1)
        if chars[i] != " ":
            chars[i] = random.choice(glitch_chars)
    return "".join(chars)

# ─────────────────────────────────────────────────────────────────────────────
# INTRO ANIMATION
# ─────────────────────────────────────────────────────────────────────────────
def play_intro():
    os.system("cls")
    lines = BANNER.strip("\n").splitlines()

    # Phase 1 — glitch in the banner
    for frame in range(18):
        os.system("cls")
        console.print()
        for l in lines:
            if frame < 10:
                display = glitch(l) if random.random() < 0.6 else l
                style   = "bold red" if random.random() < 0.4 else "bold green"
            else:
                display = l
                style   = "bold bright_green"
            console.print(Align.center(display), style=style)
        time.sleep(0.055)

    # Phase 2 — subtitle types out
    console.print()
    sub_text = Text(justify="center")
    for ch in SUBTITLE:
        sub_text.append(ch, style="bold cyan")
        console.print(Align.center(sub_text), end="\r")
        time.sleep(0.03)
    console.print()
    console.print(Align.center(TAGLINE), style=C_DIM)
    console.print()
    time.sleep(0.4)

# ─────────────────────────────────────────────────────────────────────────────
# SCANNING ANIMATION
# ─────────────────────────────────────────────────────────────────────────────
SPINNER_FRAMES = ["◐","◓","◑","◒"]
SCAN_MSGS = [
    "Probing RF spectrum...",
    "Harvesting beacon frames...",
    "Decoding 802.11 management frames...",
    "Classifying authentication schemes...",
    "Mapping SSID topology...",
    "Cross-referencing OUI database...",
    "Evaluating cipher suites...",
    "Aggregating threat vectors...",
    "Finalising recon report...",
]

def animated_scan() -> list[dict]:
    results = [None]

    def worker():
        results[0] = run_scan()

    t = threading.Thread(target=worker, daemon=True)
    t.start()

    frame = 0
    msg_i = 0
    start = time.time()

    with Live(console=console, refresh_per_second=12) as live:
        while t.is_alive() or frame < 6:
            elapsed = time.time() - start
            spin    = SPINNER_FRAMES[frame % 4]
            msg     = SCAN_MSGS[min(msg_i, len(SCAN_MSGS)-1)]
            bar_w   = 36
            bar_fill= int((elapsed / 3.0) * bar_w)
            bar_fill= min(bar_fill, bar_w)
            bar     = "█" * bar_fill + "░" * (bar_w - bar_fill)

            panel_content = Text()
            panel_content.append(f"\n  {spin} ", style="bold bright_green")
            panel_content.append(msg + "\n\n", style="bright_green")
            panel_content.append(f"  [{bar}]\n\n", style="dim green")
            panel_content.append(
                f"  TIME  {elapsed:5.2f}s   CHANNEL  SWEEP  1→165\n",
                style=C_DIM
            )

            live.update(
                Panel(panel_content,
                      title=f"[bold bright_green]  SCANNING  [/bold bright_green]",
                      border_style=C_BORDER,
                      padding=(0,2),
                      width=min(W, 72))
            )

            frame  += 1
            if frame % 6 == 0:
                msg_i += 1
            time.sleep(0.08)
            if not t.is_alive():
                time.sleep(0.15)
                break

    t.join()
    return results[0] or []

# ─────────────────────────────────────────────────────────────────────────────
# RESULTS TABLE
# ─────────────────────────────────────────────────────────────────────────────
def build_table(nets: list[dict]) -> Table:
    tbl = Table(
        box=box.SIMPLE_HEAVY,
        border_style=C_BORDER,
        header_style=f"bold {C_BORDER}",
        show_lines=True,
        padding=(0,1),
        title=f"[bold bright_green]  DETECTED NETWORKS  [/bold bright_green]",
        title_style="bold bright_green",
        caption=f"[dim green]Scan timestamp: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}[/dim green]",
    )

    tbl.add_column("#",        style="dim",            width=3,  justify="right")
    tbl.add_column("SSID",     style="bold cyan",       min_width=18, max_width=28)
    tbl.add_column("BSSID",    style="dim green",       width=19)
    tbl.add_column("VENDOR",   style="dim cyan",        width=12)
    tbl.add_column("SIGNAL",   width=14,                no_wrap=True)
    tbl.add_column("FREQ",     width=8,                 justify="center")
    tbl.add_column("CH",       style="dim",             width=4,  justify="center")
    tbl.add_column("SECURITY", width=14,                justify="center")
    tbl.add_column("GRADE",    width=5,                 justify="center")
    tbl.add_column("RADIO",    style="dim green",       width=10)

    # Sort: open first (most dangerous), then by signal strength desc
    def sort_key(n):
        a = analyse(n)
        grade_order = {"F":0,"C":1,"B":2,"B+":3,"A":4,"A+":5,"?":6}
        return (grade_order.get(a["grade"],6), -(n.get("signal",0)))

    nets_sorted = sorted(nets, key=sort_key)

    for i, net in enumerate(nets_sorted, 1):
        a   = analyse(net)
        ssid= net.get("ssid","?")
        bss = net.get("bssid","??:??:??:??:??:??")
        sig = net.get("signal", 0)
        ch  = net.get("ch",  0)
        rad = net.get("radio","?")

        grade_styles = {
            "A+":"bold green","A":"green","B+":"green",
            "B":"yellow","C":"bold yellow","F":"bold red","?":"dim"
        }
        grade_text = Text(f" {a['grade']} ", style=grade_styles.get(a["grade"],"dim"))
        sec_text   = Text(a["label"], style=a["color"])

        tbl.add_row(
            str(i),
            ssid,
            bss,
            vendor_lookup(bss)[:12],
            sig_bar(sig),
            freq_tag(ch),
            str(ch) if ch else "?",
            sec_text,
            grade_text,
            rad,
        )

    return tbl

# ─────────────────────────────────────────────────────────────────────────────
# THREAT PANEL
# ─────────────────────────────────────────────────────────────────────────────
def build_threat_panel(nets: list[dict]) -> Panel:
    lines = Text()
    found_any = False

    critical = [n for n in nets if analyse(n)["grade"] == "F"]
    weak     = [n for n in nets if analyse(n)["grade"] in ("C","B")]
    secure   = [n for n in nets if analyse(n)["grade"] in ("A","A+","B+")]

    lines.append(f"\n  NETWORKS FOUND    {len(nets):>3}\n",    style="bold green")
    lines.append(f"  CRITICAL (open)   {len(critical):>3}\n", style="bold red" if critical else "green")
    lines.append(f"  WEAK / LEGACY     {len(weak):>3}\n",     style="yellow"   if weak     else "green")
    lines.append(f"  SECURE            {len(secure):>3}\n",   style="green")
    lines.append("\n")

    if critical:
        found_any = True
        lines.append("  ⚠  OPEN NETWORKS DETECTED\n", style="bold red blink")
        for n in critical:
            lines.append(f"     → {n.get('ssid','?')[:28]} ({n.get('bssid','?')})\n",
                         style="red")
        lines.append("     Anyone within range can intercept all traffic!\n\n",
                     style="dim red")

    if weak:
        found_any = True
        lines.append("  ⚡  LEGACY ENCRYPTION\n", style="bold yellow")
        for n in weak:
            a = analyse(n)
            for r in a["risks"]:
                lines.append(f"     → {n.get('ssid','?')[:20]}  {r}\n",
                             style="yellow")
        lines.append("\n")

    if not found_any:
        lines.append("  ✓  No critical vulnerabilities detected\n", style="bold green")

    return Panel(
        lines,
        title="[bold red]  THREAT  ASSESSMENT  [/bold red]",
        border_style="red" if critical else ("yellow" if weak else "green"),
        padding=(0,1),
    )

# ─────────────────────────────────────────────────────────────────────────────
# STATS BAR
# ─────────────────────────────────────────────────────────────────────────────
def build_stats(nets: list[dict]) -> Text:
    freqs = {"2.4":0,"5":0,"?":0}
    for n in nets:
        ch = n.get("ch",0)
        if   1  <= ch <= 14:  freqs["2.4"] += 1
        elif 36 <= ch <= 177: freqs["5"]   += 1
        else:                  freqs["?"]  += 1

    bands_54  = sum(1 for n in nets if "802.11" in n.get("radio",""))
    avg_sig   = int(sum(n.get("signal",0) for n in nets) / max(len(nets),1))

    t = Text(justify="center")
    t.append(" TOTAL ", style="bold bright_green")
    t.append(f"{len(nets)}  ", style="cyan")
    t.append(" 2.4GHz ", style="bold bright_green")
    t.append(f"{freqs['2.4']}  ", style="cyan")
    t.append(" 5GHz ", style="bold bright_green")
    t.append(f"{freqs['5']}  ", style="magenta")
    t.append(" AVG SIGNAL ", style="bold bright_green")
    t.append(f"{avg_sig}%  ", style="green" if avg_sig>=50 else "yellow")
    return t

# ─────────────────────────────────────────────────────────────────────────────
# RENDER FULL SCREEN
# ─────────────────────────────────────────────────────────────────────────────
def render(nets: list[dict]):
    os.system("cls")

    # Header
    for l in BANNER.strip("\n").splitlines():
        console.print(Align.center(l), style="bold bright_green")
    console.print(Align.center(SUBTITLE),  style="bold cyan")
    console.print(Align.center(TAGLINE),   style=C_DIM)
    console.print()

    if not nets:
        console.print(Panel(
            Align.center(
                "[bold red]NO NETWORKS FOUND[/bold red]\n\n"
                "[dim]• Make sure WiFi adapter is enabled\n"
                "• Run as Administrator for better results\n"
                "• Try:  netsh wlan show networks[/dim]"
            ),
            border_style="red", padding=(1,4)
        ))
    else:
        console.print(Padding(build_table(nets), (0,2)))
        console.print()
        console.print(Padding(Align.center(build_stats(nets)), (0,2)))
        console.print()
        console.print(Padding(build_threat_panel(nets), (0,2)))

    console.print()
    console.print(Rule(style="dim green"))
    console.print(
        Align.center(
            "[dim green][ R ] RESCAN    [ S ] SORT BY SIGNAL    "
            "[ Q ] QUIT    [ H ] HELP[/dim green]"
        )
    )
    console.print(Rule(style="dim green"))

# ─────────────────────────────────────────────────────────────────────────────
# HELP PANEL
# ─────────────────────────────────────────────────────────────────────────────
def show_help():
    content = Text()
    content.append("\n  GRADE SYSTEM\n\n", style="bold bright_green")
    grades = [
        ("A+", "green",      "WPA3-SAE   — best in class, forward secrecy"),
        ("A",  "green",      "WPA2-CCMP  — strong, widely deployed"),
        ("B+", "green",      "WPA2       — strong (mixed CCMP/TKIP)"),
        ("B",  "yellow",     "WPA2-TKIP  — deprecated cipher, upgrade recommended"),
        ("C",  "bold yellow","WPA (v1)   — legacy, should be upgraded"),
        ("F",  "bold red",   "OPEN       — no encryption, highest risk"),
    ]
    for g, col, desc in grades:
        content.append(f"   {g:<4}", style=f"bold {col}")
        content.append(f"  {desc}\n", style="dim")

    content.append("\n  SIGNAL STRENGTH\n\n", style="bold bright_green")
    content.append("   ▮▮▮▮▮  80-100%  Excellent\n",  style="bright_green")
    content.append("   ▮▮▮▮▯  60-79 %  Good\n",       style="green")
    content.append("   ▮▮▮▯▯  40-59 %  Fair\n",       style="yellow")
    content.append("   ▮▮▯▯▯  20-39 %  Weak\n",       style="yellow")
    content.append("   ▮▯▯▯▯  0 -19 %  Very weak\n",  style="red")

    content.append("\n  DISCLAIMER\n\n", style="bold bright_green")
    content.append(
        "   This tool reads publicly broadcast WiFi beacons only.\n"
        "   No packets are injected or captured. No connection is made.\n"
        "   For authorised network auditing only.\n\n",
        style="dim"
    )
    console.print(Panel(content, title="[bold cyan]  HELP  [/bold cyan]",
                        border_style="cyan", padding=(0,2)))
    console.print("[dim]Press any key to return...[/dim]")
    msvcrt.getch()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────
def main():
    play_intro()

    nets = animated_scan()
    render(nets)

    sort_mode = "threat"   # threat | signal

    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch().decode(errors="ignore").lower()

            if key == "q":
                os.system("cls")
                console.print()
                console.print(Align.center(
                    "[bold bright_green]SESSION TERMINATED — GOODBYE[/bold bright_green]"
                ))
                console.print(Align.center("[dim green]stay safe out there[/dim green]"))
                console.print()
                break

            elif key == "r":
                console.print()
                console.print(Align.center(
                    "[bold bright_green]↻ INITIATING RESCAN...[/bold bright_green]"
                ))
                time.sleep(0.4)
                nets = animated_scan()
                render(nets)

            elif key == "s":
                sort_mode = "signal" if sort_mode == "threat" else "threat"
                if sort_mode == "signal":
                    nets_d = sorted(nets, key=lambda n: -n.get("signal", 0))
                else:
                    nets_d = nets
                render(nets_d)
                console.print(Align.center(
                    f"[dim cyan]Sort mode: {sort_mode.upper()}[/dim cyan]"
                ))

            elif key == "h":
                show_help()
                render(nets)

        time.sleep(0.05)


if __name__ == "__main__":
    main()
