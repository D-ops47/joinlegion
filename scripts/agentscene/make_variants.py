"""Generate the other agent-at-work scenes from the tracking template.

Same choreography, different content, so all five clips feel like one product.
One scene per HANDOVER material: pursuit, writing, decisions, tracking, comms.
"""
import re

BASE = open("tracking.html", encoding="utf-8").read()

VARIANTS = {
    "pursuit": {
        "bar": "Follow-Up Queue",
        "h1": "Follow-Up Queue",
        "h2": "Chasing so you never have to",
        "tasks": ["Find who went quiet", "Draft each follow-up",
                  "Queue the send times", "Report what came back"],
        "cols": ["Contact", "Value", "Days Quiet", "Action"],
        "rows": [
            ["Marcus Reed", "$12,400", "18", "w", "Drafted"],
            ["Tara Okafor", "$3,900", "31", "w", "Going cold"],
            ["Bishop &amp; Co.", "$27,000", "9", "d", "Sent"],
        ],
        "fieldlabel": "Draft",
        "type": "Still on your list? Happy to hold the slot - just say.",
        "rk": "Report ready &middot; 7:02 am",
        "rt": "Nine follow-ups sent. Two replied already.",
        "rs": "$43,300 back in play. Tara went 31 days quiet &mdash; second touch is queued for Thursday.",
        "chips": ["Finding who went quiet", "Building the queue",
                  "Flagging the cold ones", "Writing the follow-up"],
    },
    "writing": {
        "bar": "Drafting Desk",
        "h1": "Drafting Desk",
        "h2": "You give the point, it writes the thing",
        "tasks": ["Read the thread", "Pull the key points",
                  "Match your tone", "Draft it for approval"],
        "cols": ["Piece", "For", "Length", "Status"],
        "rows": [
            ["Proposal &mdash; Hartley", "Client", "2 pages", "d", "Ready"],
            ["Price increase note", "34 clients", "1 para", "w", "Drafting"],
            ["Monthly update", "Team", "400 words", "d", "Ready"],
        ],
        "fieldlabel": "Draft",
        "type": "Rates move 6% on the 1st. Same crew, same turnaround.",
        "rk": "Report ready &middot; 6:41 am",
        "rt": "Three drafts ready. All in your voice.",
        "rs": "The price increase note is the one you have been avoiding for five weeks. It is 90 words. Read it and hit send.",
        "chips": ["Reading the thread", "Pulling the points",
                  "Matching your tone", "Writing the draft"],
    },
    "decisions": {
        "bar": "Decision Board",
        "h1": "Decision Board",
        "h2": "Options framed, tradeoffs named",
        "tasks": ["Gather the real numbers", "Lay out the options",
                  "Name each tradeoff", "Flag what is reversible"],
        "cols": ["Option", "Cost", "Reversible", "Call"],
        "rows": [
            ["Hire a second crew", "$8.4k/mo", "No", "w", "Risk"],
            ["Raise prices 6%", "$0", "Yes", "d", "Do first"],
            ["Subcontract overflow", "Variable", "Yes", "d", "Backup"],
        ],
        "fieldlabel": "Note",
        "type": "Raise first - it is free and reversible. Hire after two months.",
        "rk": "Report ready &middot; 6:55 am",
        "rt": "One call is free and reversible. Make that one first.",
        "rs": "Raising 6% costs nothing to try and can be undone. Hiring locks in $8.4k a month before you know the demand holds.",
        "chips": ["Gathering the numbers", "Laying out options",
                  "Naming the tradeoffs", "Writing the call"],
    },
    "comms": {
        "bar": "Comms Desk",
        "h1": "Comms Desk",
        "h2": "Written down so the meeting stops needing to exist",
        "tasks": ["Capture what was said", "Write the recap",
                  "Assign the actions", "Send before anyone forgets"],
        "cols": ["Item", "Owner", "Due", "Status"],
        "rows": [
            ["Site access &mdash; Delgado", "Wilson", "Tue", "w", "Open"],
            ["Permit resubmit", "You", "Thu", "w", "Chased"],
            ["Crew swap confirmed", "Blake", "Done", "d", "Closed"],
        ],
        "fieldlabel": "Recap",
        "type": "Three actions, three owners, all dated. Nothing verbal.",
        "rk": "Report ready &middot; 7:10 am",
        "rt": "Recap sent. Every action has an owner and a date.",
        "rs": "The permit resubmit is yours and due Thursday. Everything else is assigned and moving without you.",
        "chips": ["Capturing what was said", "Writing the recap",
                  "Assigning the actions", "Sending it out"],
    },
}


def build(key, v):
    s = BASE

    # rows
    rows = ",\n  ".join(
        f"['{r[0]}', '{r[1]}', '{r[2]}', '{r[3]}', '{r[4]}']" for r in v["rows"]
    )
    s = re.sub(r"var ROWS = \[.*?\];", f"var ROWS = [\n  {rows}\n];", s, flags=re.S)

    # headings
    s = s.replace('<div class="barttl">Daily Operations</div>',
                  f'<div class="barttl">{v["bar"]}</div>')
    s = s.replace('<div class="h1">Job Tracker</div>', f'<div class="h1">{v["h1"]}</div>')
    s = s.replace('<div class="h2">Updating without being asked</div>',
                  f'<div class="h2">{v["h2"]}</div>')

    # sidebar tasks
    for i, t in enumerate(("Pull yesterday's numbers", "Update the tracker",
                           "Flag what slipped", "Write the daily report"), start=1):
        s = s.replace(f'<div class="tb"></div>{t}</div>',
                      f'<div class="tb"></div>{v["tasks"][i-1]}</div>')

    # column headers
    old = ('<tr><th style="width:34%">Job</th><th style="width:22%">Owed</th>\n'
           '              <th style="width:22%">Days Open</th><th>Status</th></tr>')
    new = (f'<tr><th style="width:34%">{v["cols"][0]}</th>'
           f'<th style="width:22%">{v["cols"][1]}</th>\n'
           f'              <th style="width:22%">{v["cols"][2]}</th>'
           f'<th>{v["cols"][3]}</th></tr>')
    s = s.replace(old, new)

    # field label + typed text
    s = s.replace('<div class="fl">Note</div>', f'<div class="fl">{v["fieldlabel"]}</div>')
    s = re.sub(r"var TYPE='[^']*';", f"var TYPE='{v['type']}';", s)

    # report
    s = s.replace('<div class="rk">Report ready &middot; 6:58 am</div>',
                  f'<div class="rk">{v["rk"]}</div>')
    s = s.replace('<div class="rt">Tracker updated. Three jobs need chasing today.</div>',
                  f'<div class="rt">{v["rt"]}</div>')
    s = re.sub(r'<div class="rs">.*?</div>', f'<div class="rs">{v["rs"]}</div>', s, flags=re.S)

    # chip copy
    for old_c, new_c in zip(("Reading the sources", "Populating the tracker",
                             "Flagging what slipped", "Writing it up"), v["chips"]):
        s = s.replace(f"say('{old_c}'", f"say('{new_c}'")

    out = f"{key}.html"
    open(out, "w", encoding="utf-8").write(s)
    return out


for k, v in VARIANTS.items():
    print("wrote", build(k, v))
