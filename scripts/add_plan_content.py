"""Add the 'what we are going to do' plan content to the card data objects."""
import re

P = "/home/ubuntu/joinlegion/card.html"
src = open(P, encoding="utf-8").read()

# ---- step 1 per WHY mode: what has to happen first ------------------------
step1 = {
    "nevertime": "Take it off your plate entirely. You already know the answer, so we do not spend a minute teaching you it again \u2014 we build the thing that executes it without you.",
    "dontknow": "Get the decision made. We force the real options into the open, name the tradeoff plainly, and commit to one. Ambiguity is the whole delay.",
    "didntstick": "Build it so it survives your worst week. The last version failed because it needed you to remember it. This one holds its own state.",
    "others": "Close the open loops. We inventory every commitment sitting unanswered, whose it is, and how long it has been there.",
    "cantsee": "Make it visible first. We do not touch the fix until you can see the shape of the problem, because everything before that is guessing.",
}

# ---- step 3 per STAKES: what the build is tuned for -----------------------
step3 = {
    "stall": "Tune it for momentum. Every week it moves something visible and tells you what moved, so progress stops being a feeling.",
    "burnout": "Tune it for relief. It never adds to your plate to keep itself running, and it batches everything into one message a day.",
    "losing": "Tune it for speed. Nothing sits, and anything going cold gets flagged before it does, not after.",
    "trapped": "Tune it for autonomy. It operates without checking in, and gets better without being told the same thing twice.",
}

# ---- step 2 per HANDOVER: what actually gets built ------------------------
step2 = {
    "pursuit": "Build the agent that does the chasing. Every follow-up, every re-approach, every nudge you keep meaning to send \u2014 drafted and queued before you think of it.",
    "writing": "Build the agent that does the writing. You supply the substance in thirty seconds of talking; it returns the finished thing, in your voice.",
    "decisions": "Build the agent that frames the calls. It lays out the options, names what you are trading away, and tells you which one you cannot walk back.",
    "tracking": "Build the agent that holds the numbers. It knows what is open, who owes what, what moved, and it reports without being asked.",
    "comms": "Build the agent that runs the communication. Agendas before, recaps after, and the follow-up that currently never gets sent.",
}

# ---- how AI actually does it, per material -------------------------------
mech = {
    "pursuit": "It watches a list, not a clock. When something has been quiet too long it writes the message, in your tone, and puts it in front of you to approve.",
    "writing": "You give it the point in a sentence. It has your previous writing as reference, so what comes back sounds like you on a good day.",
    "decisions": "It cannot want anything, which is the point. It holds every option side by side without ego and shows you the one you keep avoiding.",
    "tracking": "It reads the same sources you do, every day, without getting bored. Then it writes the summary you have been meaning to build for a year.",
    "comms": "It listens once, writes it down properly, and sends it. The meeting that existed because nobody took notes stops needing to exist.",
}

for name, d in (("STEP1", step1), ("STEP2", step2), ("STEP3", step3), ("MECH", mech)):
    lines = [f"var {name} = {{"]
    for k, v in d.items():
        esc = v.replace("\\", "\\\\").replace("'", "\\'")
        lines.append(f"  {k}:'{esc}',")
    lines[-1] = lines[-1].rstrip(",")
    lines.append("};")
    block = "\n".join(lines) + "\n\n"
    src = src.replace("/* Role is derived, not asked.", block + "/* Role is derived, not asked.", 1)

open(P, "w", encoding="utf-8").write(src)
print("added STEP1 STEP2 STEP3 MECH")
for n in ("STEP1", "STEP2", "STEP3", "MECH"):
    print(f"  {n}: {src.count('var ' + n + ' =')} definition(s)")
