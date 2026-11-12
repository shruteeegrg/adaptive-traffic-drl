#!/usr/bin/env python3
"""Bring docs/Reflective_Report_Shruti_Gurung.docx up to the final results (edits the document in place, keeping its styles).

    python scripts/update_reflective_report.py

Run it on the version of the report in git before the update (git show 41edbfd~1:docs/Reflective_Report_Shruti_Gurung.docx).
Numbers come from docs/results_final.md and the logs; the figures are figures/report/final_results.png and regime_map.png.
The simple vehicle-counting controller is called the "reference rule": it is my own implementation of standard actuated-signal logic,
not a claim about any real system.
Bracketed prompts in the report ([edit ...], [Add ...]) are for the student's own words and are left in place.
"""
import copy
import os

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm
from docx.text.paragraph import Paragraph

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "docs", "Reflective_Report_Shruti_Gurung.docx")
d = docx.Document(PATH)


def find(prefix):
    for p in d.paragraphs:
        if p.text.startswith(prefix):
            return p
    raise SystemExit(f"paragraph not found: {prefix}")


def set_runs(p, *texts):
    """Put `texts` into the first runs (keeping their formatting) and drop the rest."""
    for r, t in zip(p.runs, texts):
        r.text = t
    for r in p.runs[len(texts):]:
        r._r.getparent().remove(r._r)


def clone_after(anchor_el, template_el, *texts):
    el = copy.deepcopy(template_el)
    anchor_el.addnext(el)
    p = Paragraph(el, None)
    set_runs(p, *texts)
    return p


def set_cell(cell, text):
    runs = cell.paragraphs[0].runs
    runs[-1].text = text
    for r in runs[:-1]:
        r.text = ""


def table_after(caption_text):
    cap = find(caption_text)
    el = cap._p.getnext()
    assert el.tag.endswith("}tbl"), caption_text
    return docx.table.Table(el, cap._parent)


def fill_rows(tbl, rows):
    """Make the table have len(rows) rows (header included) and write the text in."""
    while len(tbl.rows) < len(rows):
        tbl._tbl.append(copy.deepcopy(tbl.rows[-1]._tr))
    while len(tbl.rows) > len(rows):
        tbl._tbl.remove(tbl.rows[-1]._tr)
    for r, row in zip(tbl.rows, rows):
        for c, text in zip(r.cells, row):
            set_cell(c, text)


# ---------------------------------------------------------------- 1. introduction and context
set_runs(find("My project is an adaptive"),
         "My project is an adaptive traffic signal controller. Most traffic lights run on a fixed timer and cannot react when one road is "
         "jammed while another is empty. I built a controller that learns to choose which direction gets green by trial and error, using a "
         "Deep Q-Network (DQN) written from scratch, and tested it in the SUMO traffic simulator against a fixed-time controller. I also wrote a "
         "simple vehicle-counting controller (the reference rule) to check whether learning adds anything over a simple method. It is aimed at "
         "traffic agencies, municipalities and smart-city planners. This report looks back at the work, compares it with the plan in my proposal, "
         "explains what went well and what went wrong, and sets out the work that remains.")

aim = find("The aim is to show")
clone_after(aim._p.getprevious(), aim._p,
            "What the product is. The project delivers a software package (traffic_drl) with a command-line tool and a live demo. It reads the "
            "number of vehicles on each road of a junction and decides, every 5 simulated seconds, which direction gets green. A municipality or "
            "traffic agency would use it to estimate, in a simulator and before any road trial, how much waiting a smarter signal could save at a "
            "junction. It is not connected to real signals or real traffic data, and it covers one simulated junction. Nepal's first AI-enabled "
            "signals in Lalitpur are reported to count vehicles (Onlinekhabar, 2024); how they decide is not published, so nothing here claims to "
            "reproduce them.")

for prefix, text in (
        ("O1 simulate", "Objective 1 (build the junction): simulate a realistic intersection in SUMO;"),
        ("O2 design", "Objective 2 (design the network): design a custom neural network as the Q-value function approximator;"),
        ("O3 implement", "Objective 3 (write the training loop): implement the training loop (action selection, reward, backpropagation) from scratch;"),
        ("O4 show", "Objective 4 (show that it helps): show that the agent reduces congestion metrics compared with a fixed timer.")):
    set_runs(find(prefix), text)

set_runs(find("The method was incremental"),
         "The method was incremental, to limit the convergence risk named in the proposal: a Q-table on a simplified problem first, then the "
         "neural network and DQN on the full intersection. I planned ten weekly milestones (repository and environment, SUMO network, Q-table, "
         "state and reward design with the network, DQN loop, tuning, visualisation, baseline and demo app, comparative analysis, final report). "
         "I kept this plan, but I worked through the early milestones faster than planned. Three changes were made on purpose. The proposal "
         "listed PyTorch or TensorFlow, but I wrote the network by hand in NumPy, including backpropagation, so that Objectives 2 and 3 are met "
         "literally. I measured success with the number of vehicles waiting rather than queue length alone, after finding that queue length hides "
         "vehicles stuck outside a full road (Section 4). And I added a second comparison beyond the proposal's fixed timer: a simple "
         "vehicle-counting reference rule, based on standard actuated-signal logic (a minimum and a maximum green time, and a switch when a side "
         "empties or the other side is much busier). A fixed timer is easy to beat, so the reference rule lets me ask when a learned controller is "
         "worth it compared with a simple method. The design diagrams (business context, use case, class, data flow, entity-relationship, "
         "functional and system architecture, sequence, activity and workflow) are in Appendix A.")

# ---------------------------------------------------------------- 3. reflection
fill_rows(table_after("Table 1:"), [
    ["#", "Milestone", "Planned", "Actual", "%"],
    ["1", "Repository, environment, package", "Week 1", "Done early", "100"],
    ["2", "SUMO network and config schema", "Week 2", "Done early", "100"],
    ["3", "Q-table baseline", "Week 3", "Done early; verified on real SUMO", "100"],
    ["4", "State/reward design, neural network", "Week 4", "Done early; gradient-checked", "100"],
    ["5", "DQN training loop", "Week 5", "Done early", "100"],
    ["6", "Training, tuning, checkpoints", "Week 6", "Done; unstable training fixed by learning from demonstrations", "100"],
    ["7", "Visualisation module", "Week 7", "Plots, live chart, regime map and results figure done", "100"],
    ["8", "Fixed-time baseline, scenarios, demo app", "Week 8", "Done, plus reference rule, compare command, demo with three controllers", "100"],
    ["9", "Comparative analysis", "Week 9", "100-episode tests with statistics: 16 demand patterns and Kathmandu-style traffic", "100"],
    ["10", "Final report and polish", "Week 10", "Started; structure and results written", "25"],
    ["–", "Contextual report (literature review)", "Not scheduled", "Submitted; supervisor asked for more critical synthesis", "60"],
])

set_runs(find("I was ahead of plan"),
         "I was ahead of plan on the build milestones, because I worked in short, tested steps and reused each piece. The extra time went into the "
         "question that mattered most: whether the agent really beats a good baseline. That was harder than building the agent. The agent beat the "
         "fixed timer, and matched a simple reference rule but did not reliably beat it (Section 4). Two items remain: the critical synthesis in the literature review, which "
         "my supervisor asked for, and the final report.")

set_runs(find("The high points were"),
         "The high points were seeing the first Q-table agent learn on the real simulator, and, much later, seeing the DQN match the reference rule "
         "after weeks of unstable training, once I gave it the rule's demonstrations [edit to your own words: how did this feel?]. The low points "
         "were discovering that my first agent was cheating, then that my own first reference rule was wrong, and later that my first "
         "Kathmandu-style traffic was so heavy that no controller could help [edit: confirm]. Each time the problem became clear only after I "
         "looked at a measurement I had not planned to look at, which taught me to be more suspicious of good-looking numbers, and of "
         "bad-looking ones.")

set_runs(find("I wrote a weekly log"),
         "I wrote a weekly log and a progress report for my supervisor, worked in small tested commits, and wrote automated tests (about 140) so "
         "that I could change code without breaking earlier results. Each experiment had a written question, and from the benchmark onwards the "
         "decision rule was fixed before the results came in. Results tables and figures are rebuilt from saved files by scripts, and I checked "
         "the install on clean Windows and Mac machines, which found three real problems that I then fixed. What I did not keep up: documentation "
         "sometimes fell behind the code, and I started the literature review late. My work computer could not install SUMO, so I developed on one "
         "machine and ran real simulations on a second one. That cost time in hand-offs, and a long training run once stalled when the laptop went "
         "to sleep. I changed my routine by turning off sleep, adding a resume feature to the experiment runner, and writing a pre-demo checklist. "
         "Because the Windows laptop will not be at the demo, I set up and tested the demo on a Mac as well.")

fb = find("[Add after the demo")
clone_after(fb._p.getprevious(), fb._p,
            "My supervisor said that the contextual report showed good technical depth and that starting with a Q-table showed mature judgement, "
            "but that the literature review lacks critical synthesis and is mostly descriptive summaries. I will act on this by building a "
            "comparison table of the studies (method, state, reward, baseline, scenario, result), by showing where they disagree, and by linking "
            "each point to what my own results show, for example that a simple reference rule is a strong baseline.")
# the new paragraph is upright text, not the italic placeholder style
for r in Paragraph(fb._p.getprevious(), None).runs:
    r.italic = False

# ---------------------------------------------------------------- 4. critical analysis
heading = find("4. Critical analysis")
tpl_title = copy.deepcopy(find("Problem 1:")._p)
tpl_body = copy.deepcopy(find("Problem 1:")._p.getnext())
old = []
el = heading._p.getnext()
o4 = find("Objective O4:")._p
while el is not o4:
    old.append(el)
    el = el.getnext()
problems = [
    ("Problem 1: ", "The agent cheated.",
     "The first DQN learned to flip the signal at every decision, about 450 switches per 30-minute episode. The cause was that reward was "
     "charged per decision, so a switch (which takes about 4 s including yellow) hid the congestion that yellow caused. I fixed it by charging "
     "cost for every simulated second, yellow included, and added a regression test comparing a flip policy with a hold policy. Lesson: track "
     "behaviour (here, the switch count), not only the reward."),
    ("Problem 2: ", "A metric hid the congestion.",
     "Approach roads hold only about 12 vehicles, so under heavy demand cars wait outside the network and queue length stays flat while delay "
     "grows. I added a backlog measure and now rank controllers by vehicles waiting (queue plus backlog). Lesson: check that the metric "
     "measures what I think it measures."),
    ("Problem 3: ", "My first reference rule was wrong.",
     "My first version of the reference rule counted only stopped vehicles. While a road has green its vehicles are moving, so the rule saw "
     "almost nothing and switched at once, and it lost to the fixed timer by 12% to 131%. I noticed because tuning its maximum green and its "
     "ratio changed nothing. I rewrote it to count all vehicles on the road, as a detector would, and chose its settings on separate seeds. "
     "Lesson: when a tuning knob does nothing, my model of the system is probably wrong."),
    ("Problem 4: ", "A simple reference rule beat my agent.",
     "In the fair comparison (100 fresh-seed runs, confidence intervals, significance tests) the reference rule beat every early DQN: on "
     "tidal traffic 7.2 against 10.1 for my best agent, and on rush hour 126.6 against 139.8. Training was also unstable: agents were good "
     "early and worse later. I gave the DQN the same vehicle counts as the rule and tried Double DQN (van Hasselt et al., 2016), slow target "
     "updates, gradient clipping, learning-rate decay and the rule's experience in the replay memory, with only partial success (2 of 4 runs "
     "stayed good on tidal). What worked was learning from demonstrations (Hester et al., 2018): the rule's decisions are kept in a frozen "
     "memory that is never overwritten, and a margin loss stops the network drifting away from them. After that the DQN matched the rule in "
     "every scenario and, in some heavy, uneven cases, beat it, but not reliably. The agents were trained from the rule's demonstrations, so "
     "matching it is expected; the interesting cases are where they went beyond it. Lesson: the baseline decides how good a result looks."),
    ("Problem 5: ", "My first Kathmandu-style traffic overloaded the junction.",
     "I added motorcycles, buses and turning vehicles. At 900 and 1,100 vehicles per hour per road the junction passed only about 1,800 "
     "vehicles per hour in total, and the reference rule behaved exactly like the fixed timer. Two diagnostic scenarios showed why: turning "
     "vehicles, not the mixed fleet, halve a single lane's capacity (cars going straight 3,025 vehicles per hour, mixed fleet going straight "
     "3,232, cars with turns 1,650). I recalibrated the demand to the measured capacity. The vehicle mix (62% motorcycles, 22% cars, 8% buses, "
     "8% light goods) is an assumption that I still have to check against its source. Lesson: calibrate a scenario before drawing conclusions "
     "from it."),
    ("Problem 6: ", "One model for every pattern still fails.",
     "A single model trained on twelve random demand patterns did not match the reference rule on three scenarios it had not seen (rush hour "
     "128 to 145 against 126.6, and worse on light traffic). In all four runs the best version was the one right after copying the rule, so "
     "further training added nothing. I report it as a negative result and keep one specialist model per scenario. I do not know why, and "
     "any explanation would be a hypothesis."),
]
anchor = heading._p
for lead, title, body in problems:
    anchor = clone_after(anchor, tpl_title, lead, title)._p
    anchor = clone_after(anchor, tpl_body, body)._p
for el in old:
    el.getparent().remove(el)

set_runs(find("Objective O4:"), "Objective 4: ", "Results against my target.")
set_runs(find("I will keep the plan current"),
         "I will keep the plan current by updating the README checklist whenever I finish a milestone and by reviewing this table at each "
         "weekly supervisor meeting.")
set_runs(find("Table 2:"), "Table 2: Final tests, 100 episodes of 30 simulated minutes on fresh seeds (vehicles waiting, lower is better; the DQN column "
                           "gives the range of four independently trained agents)")
fill_rows(table_after("Table 2:"), [
    ["Situation", "Fixed timer / reference rule", "DQN agents (range)", "Outcome"],
    ["Morning commute: heavy one way, then the other (tidal)", "114.0 / 7.2", "6.9 to 7.4", "About 94% less waiting than the fixed timer; DQN level with the reference rule"],
    ["Evening rush: every road busy (rush hour)", "138.3 / 126.6", "122.2 to 126.6", "DQN up to 12% below the fixed timer; level with the reference rule"],
    ["Busy Kathmandu street: motorcycles, buses, turns, near capacity", "11.5 / 8.8", "7.6 to 8.0", "DQN 30% to 34% below the fixed timer; about one vehicle below the reference rule"],
    ["Quiet hours (low traffic)", "1.5 / 0.2", "0.5 (mixed model)", "All near zero; the DQN switches the lights far more often than needed"],
])

res = find("I therefore met the target")
set_runs(res,
         "Against the fixed timer the target is met wherever the traffic gives control something to work with: about 94% less waiting on the "
         "commute pattern and about 10% on the evening rush, and the reference rule does the same. Against the reference rule the DQN matches it "
         "in every situation. In heavy, uneven traffic 3 of 12 agents were significantly better (5% to 11%) and 2 were worse; across all 32 "
         "specialist agents the count is 3 better, 3 worse and 26 ties or small differences (Figure 1). I report that as it is: the learned "
         "controller reaches the level of a simple reference rule, but I cannot claim it beats the rule in general. The agents were trained from "
         "the rule's demonstrations, which is why matching it is expected. I chose the metric and the decision rule before the results came in.")
cap_tpl = copy.deepcopy(find("Figure A1:")._p)
pic_tpl = None
anchor = res._p
for fname, caption in (("final_results.png", "Figure 1: Each dot is one independently trained agent, compared with the reference rule "
                                              "(changes beyond 30% are drawn at the edge)"),
                       ("regime_map.png", "Figure 2: Where the reference rule helps against a fixed timer, by demand level and unevenness "
                                          "(30 episodes per cell)")):
    pic_par = d.add_paragraph()
    pic_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic_par.add_run().add_picture(os.path.join(ROOT, "figures", "report", fname), width=Cm(13.5))
    anchor.addnext(pic_par._p)
    anchor = clone_after(pic_par._p, cap_tpl, caption)._p

# ---------------------------------------------------------------- 5-8
set_runs(find("Technical skills I gained"),
         "Technical skills I gained, with evidence in the repository: configuring SUMO and controlling it with TraCI; tabular Q-learning and DQN, "
         "including Double DQN and learning from demonstrations; a neural network with backpropagation written in NumPy and verified against a "
         "numerical gradient; experiment design with separate training, selection and test seeds and a decision rule fixed in advance; "
         "statistics for comparing controllers (confidence intervals, Welch and paired t-tests, effect size) written without a statistics "
         "library; building an installable, config-driven Python package with a command-line tool, plots and a Streamlit demo; and testing code "
         "that talks to a simulator by using a fake interface.")
s = find("Strengths:")
set_runs(s, s.text.replace("I started the literature review late", "I started the literature review late and it still needs critical synthesis")
         if "I started the literature review late" in s.text else s.text)

fill_rows(table_after("Table 3:"), [
    ["Action", "Due", "Done when"],
    ["Make the demo show today's fixed timer against the smart signal in four plain-language situations", "Week 8", "Demo shows four named situations with before/after numbers in seconds and vehicles"],
    ["Give the demo on the main laptop, with the second laptop and a screen recording as backups", "Week 8", "Live demo runs on both machines and the recording is saved"],
    ["Rewrite the literature review with critical synthesis (comparison table, where studies disagree, link to my results)", "Weeks 8–9", "Draft sent to my supervisor"],
    ["Write the final report (methods, results, discussion, conclusion)", "Weeks 8–10", "Complete draft reviewed by my supervisor"],
    ["Check the sources I rely on: Hester et al. (2018), van Hasselt et al. (2016), the vehicle-mix source", "Week 8", "Each checked against the original and the text corrected"],
    ["Fix the survey figures in the contextual report", "Week 9", "Figures labelled as real responses; form matches the appendix"],
    ["Re-check a clean install and the tagged release before submission", "Week 10", "Install and demo run from a clean clone"],
])

c2 = find("Chapter 2:")
set_runs(c2, "Chapter 2: Background and literature review. ",
         "Fixed-time and vehicle-actuated control (and the reported Lalitpur pilot, whose algorithm is not published); reinforcement learning (Q-learning, DQN, "
         "Double DQN, learning from demonstrations); related work on RL for signal control, read critically; SUMO and TraCI; the gap this "
         "project addresses.")
c6 = find("Chapter 6:")
set_runs(c6, "Chapter 6: Results. ",
         "Each target with how it was measured: the fair comparison of fixed timer, reference rule and DQN over 100 fresh-seed runs; the regime "
         "map over 16 demand patterns; specialist agents, Kathmandu-style traffic and the single-model experiment; training stability and the "
         "effect of learning from demonstrations.")
c7 = find("Chapter 7:")
set_runs(c7, "Chapter 7: Evaluation. ",
         "Results against the objectives and the literature; limitations (one junction with one lane per road, an assumed vehicle mix, one "
         "model per scenario, seed sensitivity); project management.")
c8 = find("Chapter 8:")
set_runs(c8, "Chapter 8: Conclusions and further work. ",
         "Summary; further work (multi-lane junctions with motorcycle filtering, real traffic counts, one general model, several junctions); "
         "personal reflection.")

set_runs(find("The build is ahead of plan"),
         "The build is complete and the core objectives are met: a SUMO intersection, a hand-written network and DQN, and a fair comparison with "
         "a fixed timer. Adaptive control, learned or rule-based, clearly beats a fixed timer wherever the traffic gives it something to work "
         "with: about 94% less waiting on commute-style traffic and about 10% on a busy evening rush. A simple reference rule gets almost all of "
         "that benefit. The learned controller, trained from the rule's demonstrations, matches the rule and sometimes beats it by about 10% in "
         "heavy, uneven traffic, but not reliably, and I do not yet have one model for every pattern. The main lessons are to choose the "
         "baseline carefully, to look at behaviour as well as reward, to test on data I did not choose from, and to report mixed results "
         "plainly. I will follow the action plan above, starting with the demo and the literature review.")

# ---------------------------------------------------------------- references (details to be checked by the student)
lopez = find("Lopez, P.A.")
clone_after(lopez._p.getprevious(), lopez._p,
            "Hester, T. et al. (2018) ‘Deep Q-learning from demonstrations’, Proceedings of the AAAI Conference on Artificial Intelligence, "
            "32(1). [check the details against the original before submitting]")
mnih = find("Mnih, V.")
clone_after(mnih._p, lopez._p,
            "Onlinekhabar (2024) Nepal's first intelligent traffic lights operational from Kupondole to Jawalakhel. Available at: "
            "https://english.onlinekhabar.com/nepals-first-intelligent-traffic-lights-operational-from-kupondole-to-jawalakhel.html "
            "(Accessed: [add date]).")
last = find("SUMO Documentation")
clone_after(last._p, lopez._p,
            "van Hasselt, H., Guez, A. and Silver, D. (2016) ‘Deep reinforcement learning with double Q-learning’, Proceedings of the AAAI "
            "Conference on Artificial Intelligence, 30(1). [check the details against the original before submitting]")

for p in d.paragraphs:
    for word in ("density", "Density", "tuned rule", "Lalitpur"):
        if word in p.text:
            print("check wording:", word, "|", p.text[:90])
d.save(PATH)
print("saved", PATH)
