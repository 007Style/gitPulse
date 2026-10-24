"""Regenerate docs/example-output.svg (a colored terminal screenshot for the README)."""
import os
from xml.sax.saxutils import escape

rows = """acorn3            main    +1           synced      2mo
acorn4            main    clean        synced      2mo
banner            main    clean        synced      58d
beeBridge         main    clean        synced      2mo
cowntdown         main    ?1           synced      55d
cp                main    clean        synced      53d
DepthsOfMalachar  main    clean        synced      24d
diskPulse         main    ?1           synced      59d
MaRTIni-legacy    main    clean        synced       1h
MaRTIni-v1        main    clean        synced      53d
MaRTIni-v2        main    clean        synced      53d
MaRTIni-v3        master  ?1           synced      53d
moo++             main    clean        synced      20d
netPing           main    ?1           synced      58d
portWatch         main    ?2           synced      59d
PPC2ARM           main    ?3           synced      24d
PPC2x86           main    clean        synced      58d
procTree          main    clean        synced      12m
deepThink         main    clean        synced      2mo
deepThinkER       main    clean        no upstream   2mo
WingmanAI         main    clean        synced      2mo
qrTxtGen          main    ?4           synced      44d
socks             main    clean        synced      53d
spacePirates      main    ?2           synced      46d
threads           main    ?2           synced      53d""".split("\n")

header = "REPO              BRANCH  DIRTY        SYNC         LAST  STALE"
summary = "25 repos | 10 dirty | 0 ahead | 0 behind | 0 stale branches"
FG, CY, GR, YE, DM = "#d4d4d4", "#56d4dd", "#5fd35f", "#e5c07b", "#7f848e"


def span(t, c, bold=False):
    w = ' font-weight="bold"' if bold else ""
    return '<tspan fill="%s"%s>%s</tspan>' % (c, w, escape(t))


lines = [span(header, FG, True)]
for r in rows:
    name, mid, dirty, rest = r[:16], r[16:26], r[26:38], r[39:]
    if rest.startswith("no upstream"):
        sync, tail, sc = "no upstream", rest[11:].strip().rjust(5), DM
    else:
        sync, tail, sc = "synced     ", rest[6:].strip().rjust(5), GR
    tail = " " + tail + "  "
    dc = GR if dirty.strip() == "clean" else YE
    lines.append(span(name, CY) + span(mid, FG) + span(dirty, dc) +
                 span(r[38:39], FG) + span(sync, sc) + span(tail, FG))
lines += ["", span(summary, FG)]

lh, x, y0, w = 20, 20, 64, 760
h = y0 + (len(lines) + 1) * lh + 10
cmd = span("$ ", GR, True) + span("gitPulse -r ~/Documents/Bob -d 3 -s 60", FG)
out = [
    '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-label="gitPulse example output">' % (w, h, w, h),
    '<rect width="%d" height="%d" rx="10" fill="#1e1e1e"/>' % (w, h),
    '<rect width="%d" height="30" rx="10" fill="#323232"/><rect y="20" width="%d" height="10" fill="#323232"/>' % (w, w),
    '<circle cx="18" cy="15" r="6" fill="#ff5f56"/><circle cx="38" cy="15" r="6" fill="#ffbd2e"/><circle cx="58" cy="15" r="6" fill="#27c93f"/>',
    '<text x="%d" y="20" fill="#9da5b4" font-size="12" text-anchor="middle" font-family="-apple-system,Segoe UI,sans-serif">gitPulse</text>' % (w // 2),
    '<g font-family="Menlo,Monaco,Consolas,\'Courier New\',monospace" font-size="14" xml:space="preserve">',
    '<text x="%d" y="%d" xml:space="preserve">%s</text>' % (x, y0 - 12, cmd),
]
for k, l in enumerate(lines):
    out.append('<text x="%d" y="%d" xml:space="preserve">%s</text>' % (x, y0 + (k + 1) * lh, l))
out.append("</g></svg>")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "example-output.svg"), "w").write("\n".join(out))
