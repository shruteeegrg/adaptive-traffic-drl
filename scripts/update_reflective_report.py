#!/usr/bin/env python3
"""Rewrite docs/Reflective_Report_Shruti_Gurung.docx for readers who do not know the project (edits the document in place, keeping its styles).

    git show 41edbfd~1:docs/Reflective_Report_Shruti_Gurung.docx > docs/Reflective_Report_Shruti_Gurung.docx   # the version before the rewrite
    python scripts/update_reflective_report.py

Scope: the work up to Week 8. Terms are defined in plain words; no demo, no mention of the machines used. The simple vehicle-counting
controller is called the "reference rule". Numbers come from docs/results_final.md and the logs; figures are figures/report/final_results.png
and regime_map.png. Bracketed prompts ([edit ...], [Add ...]) are for the student's own words and are left in place.
"""
import copy
import os

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt
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


def new_table_after(anchor_el, rows, widths_cm):
    t = d.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = d.styles["Table Grid"]
    for i, row in enumerate(rows):
        for j, text in enumerate(row):
            cell = t.cell(i, j)
            cell.width = Cm(widths_cm[j])
            run = cell.paragraphs[0].add_run(text)
            run.font.size = Pt(10)
            run.bold = i == 0
    anchor_el.addnext(t._tbl)
    return t


# templates taken before anything is changed
TPL_BODY = copy.deepcopy(find("The aim is to show")._p)
TPL_BULLET = copy.deepcopy(find("O1 simulate")._p)
TPL_CAPTION = copy.deepcopy(find("Table 1:")._p)
TPL_HEADING2 = copy.deepcopy(find("3.4 Feedback")._p)
TPL_TITLE = copy.deepcopy(find("Problem 1:")._p)
TPL_PROBLEM_BODY = copy.deepcopy(find("Problem 1:")._p.getnext())
TPL_FIGCAP = copy.deepcopy(find("Figure A1:")._p)
TPL_REF = copy.deepcopy(find("Lopez, P.A.")._p)

# ---------------------------------------------------------------- 1. introduction and context
set_runs(find("My project is an adaptive"),
         "Most traffic lights run on a fixed timer: every direction gets the same green time in a loop, so an empty road still gets its full "
         "green while a jammed road waits. My project is an adaptive traffic signal controller that looks at the traffic and decides which "
         "direction gets green. I built it with a Deep Q-Network (DQN), a program that learns by trial and error, written from scratch, and I "
         "tested it in SUMO, a free traffic simulator, against a fixed timer. I also developed a very simple controller based on counting "
         "vehicles in each street (the reference rule), to check whether learning adds anything over a simple method. The work is aimed at "
         "traffic agencies, municipalities and smart-city planners. This report looks back at the work up to Week 8, compares it with the plan "
         "in my proposal, explains the hurdles I met and how I overcame them, and sets out the work that remains. Box 1 explains the main "
         "terms in plain words.")

heading2 = find("2. Context and description")
product = clone_after(heading2._p, TPL_BODY,
                      "What the product is. The project delivers a software package (traffic_drl) with a command-line tool. It reads the number "
                      "of vehicles on each road of a junction and decides, every 5 simulated seconds, which direction gets green. A municipality "
                      "or traffic agency could use it to estimate, in a simulator and before any road trial, how much waiting a smarter signal "
                      "could save at a junction. It is not connected to real signals or real traffic data, and it covers one simulated junction. "
                      "Nepal's first AI-enabled signals in Lalitpur are reported to count vehicles (Onlinekhabar, 2024); their method is not "
                      "published, so the reference rule used here is my own simple version of the idea.")
box_cap = clone_after(product._p, TPL_CAPTION, "Box 1: Key terms in plain words")
new_table_after(box_cap._p, [
    ["Term", "In plain words"],
    ["SUMO", "A free traffic simulator. It moves every vehicle second by second, so a signal controller can be tested without a real road."],
    ["Fixed timer", "The usual traffic light: each direction gets the same green time, in a loop, whatever the traffic."],
    ["Reference rule", "A very simple controller based on counting vehicles in each street. It gives green to the busier street, within a "
                       "minimum and a maximum green time. It does not learn. I wrote it as a fair, simple comparison."],
    ["DQN agent", "A program that learns which choice is best by trying choices in the simulator and being scored. A small neural network "
                  "estimates how good each choice is. I wrote it from scratch in NumPy, with no reinforcement-learning library."],
    ["Choice (action)", "Every 5 simulated seconds the controller either keeps the current green or switches to the other direction "
                        "(a 3-second yellow is added automatically)."],
    ["Reward", "The agent's score: fewer vehicles waiting means a better score."],
    ["Vehicles waiting", "The main measure. Vehicles stopped on the roads, plus vehicles held outside because a road is full, averaged over a "
                         "30-minute run. Lower is better."],
    ["Seed", "A number that makes random traffic repeatable, so every controller can be tested on exactly the same traffic."],
    ["Learning from demonstrations", "Starting the agent by showing it the reference rule's decisions, and keeping them in its memory while it trains."],
], [3.6, 12.4])

for prefix, text in (
        ("O1 simulate", "Objective 1 (build the junction): simulate a realistic intersection in SUMO;"),
        ("O2 design", "Objective 2 (design the network): design a custom neural network as the Q-value function approximator;"),
        ("O3 implement", "Objective 3 (write the training loop): implement the training loop (action selection, reward, backpropagation) from scratch;"),
        ("O4 show", "Objective 4 (show that it helps): show that the agent reduces congestion metrics compared with a fixed timer.")):
    set_runs(find(prefix), text)

set_runs(find("The method was incremental"),
         "The method was incremental, to limit the convergence risk named in the proposal (the risk that the agent never learns anything "
         "useful): a lookup-table learner (a Q-table) on a simplified problem first, then the neural network and DQN on the full junction. I "
         "planned ten weekly milestones (repository and environment, SUMO network, Q-table, state and reward design with the network, DQN loop, "
         "tuning, visualisation, baseline and scenarios, comparative analysis, final report). I kept this plan, but I worked through the early "
         "milestones faster than planned. Three changes were made on purpose. The proposal listed PyTorch or TensorFlow, but I wrote the network "
         "by hand in NumPy, including backpropagation (the learning step), so that Objectives 2 and 3 are met literally. I measured success with "
         "the number of vehicles waiting rather than queue length alone, after finding that queue length hides vehicles stuck outside a full road "
         "(Section 4). And I added a second comparison beyond the proposal's fixed timer: the reference rule, based on standard "
         "actuated-signal logic (a minimum and a maximum green time, and a switch when a street empties or the other street is much busier). A "
         "fixed timer is easy to beat, so the reference rule lets me ask whether a learned controller is worth it compared with a simple method. "
         "The design diagrams (business context, use case, class, data flow, entity-relationship, functional and system architecture, sequence, "
         "activity and workflow) are in Appendix A.")

# ---------------------------------------------------------------- 3. reflection
fill_rows(table_after("Table 1:"), [
    ["#", "Milestone", "Planned", "Actual", "%"],
    ["1", "Repository, environment, package", "Week 1", "Done early", "100"],
    ["2", "SUMO network and config schema", "Week 2", "Done early", "100"],
    ["3", "Q-table baseline", "Week 3", "Done early; verified on real SUMO", "100"],
    ["4", "State/reward design, neural network", "Week 4", "Done early; gradient-checked", "100"],
    ["5", "DQN training loop", "Week 5", "Done early", "100"],
    ["6", "Training, tuning, checkpoints", "Week 6", "Done; unstable training fixed by learning from demonstrations", "100"],
    ["7", "Visualisation module", "Week 7", "Plots and results figures done", "100"],
    ["8", "Fixed-time baseline and scenarios", "Week 8", "Done, plus the reference rule, a compare command with statistics, Kathmandu-style traffic", "100"],
    ["9", "Comparative analysis", "Week 9", "Tests run (100 episodes each); written analysis still to do", "60"],
    ["10", "Final report and polish", "Week 10", "Not started; first outline written", "10"],
    ["–", "Contextual report (literature review)", "Not scheduled", "Submitted; supervisor asked for more critical synthesis", "60"],
])

set_runs(find("I was ahead of plan"),
         "Up to Week 8 I completed the build milestones ahead of plan, because I worked in short, tested steps and reused each piece. The extra "
         "time went into the question that mattered most: whether the agent really beats a good comparison. That was harder than building the "
         "agent. The agent beat the fixed timer, and matched the simple reference rule but did not reliably beat it (Section 4). Three items "
         "remain: the written comparative analysis, the critical synthesis in the literature review that my supervisor asked for, and the "
         "final report.")

set_runs(find("The high points were"),
         "When I started, I did not know how to connect a learning program to a traffic simulator, how to write a neural network's learning "
         "step by hand, or how to tell a program that has really learned from one that has just been lucky [edit to match what is true for "
         "you]. The high points were seeing the first lookup-table learner improve on the real simulator, and, much later, seeing the agent "
         "match the reference rule after weeks of unstable training, once I showed it the rule's decisions [edit to your own words: how did "
         "this feel?]. The low points were finding that my first agent was cheating, that my first reference rule was wrong, and that my first "
         "Kathmandu-style traffic was so heavy that no controller could help [edit: confirm]. Each time the problem became clear only after I "
         "looked at a measurement I had not planned to look at. That taught me to be suspicious of numbers that look good, and of numbers "
         "that look bad.")

set_runs(find("I wrote a weekly log"),
         "I kept a weekly log and a progress report for my supervisor, worked in small tested commits, and wrote automated tests (about 140) so "
         "that I could change code without breaking earlier results. Every experiment had a written question first, and once I started "
         "comparing controllers I wrote down how I would judge the result before I saw it. Training runs take hours, so I wrote scripts that "
         "save every result and can resume an interrupted run, and the tables and figures in my reports are rebuilt from the saved files, not "
         "typed by hand. What I did not keep up: documentation sometimes fell behind the code, and I started the literature review late.")

fb = find("[Add after the demo")
sup = clone_after(fb._p.getprevious(), fb._p,
                  "My supervisor said that the contextual report showed good technical depth and that starting with a Q-table showed mature "
                  "judgement, but that the literature review lacks critical synthesis and is mostly descriptive summaries. I will act on this by "
                  "building a comparison table of the studies (method, state, reward, comparison used, traffic, result), by showing where they "
                  "disagree, and by linking each point to what my own results show, for example that a simple reference rule is a strong "
                  "comparison.")
for r in sup.runs:
    r.italic = False
set_runs(fb, "[Add any feedback from my supervisor on this project's progress, and what I will change because of it.]")

h35 = clone_after(fb._p, TPL_HEADING2, "3.5 Advice for a student starting this project")
intro35 = clone_after(h35._p, TPL_BODY,
                      "Looking back, these are the things I wish I had been told on the first day. Each one comes from something that cost me "
                      "time.")
anchor = intro35._p
for text in (
        "Build the smallest version that works from end to end first (here, a lookup-table learner on a toy traffic model) and add the "
        "neural network only after that. When something then fails, you know which new piece caused it.",
        "Expect the agent to find loopholes. Look at what it does (for example how often it switches the light), not only its score, and write "
        "a test for every cheat you find.",
        "Decide how you will judge results before you run them: separate random traffic for tuning and for the final test, enough runs to see "
        "the spread, and a rule for what counts as a real improvement.",
        "Compare with a simple method early, not only with a fixed timer. A simple method can beat a clever one, and finding that out late is "
        "expensive.",
        "Expect training to be unstable and runs to take hours. Keep a log of each experiment and the question it answers, and script your runs "
        "so they save results and can be resumed.",
        "Check that your test traffic can be influenced at all. If the junction is jammed, every controller looks the same.",
        "Expect negative results, and report them. A clear 'this did not work' is more useful than a result tuned until it looks good."):
    anchor = clone_after(anchor, TPL_BULLET, text)._p

# ---------------------------------------------------------------- 4. critical analysis
heading = find("4. Critical analysis")
old = []
el = heading._p.getnext()
o4 = find("Objective O4:")._p
while el is not o4:
    old.append(el)
    el = el.getnext()
problems = [
    ("Problem 1: ", "I did not know where to start.",
     "I had to combine two things that were new to me [confirm]: a traffic simulator (SUMO) and a learning method (reinforcement learning, "
     "where a program learns by trying actions and being scored). Doing both at once meant that when nothing worked I could not tell which "
     "part was broken. I stopped and built the project in small steps instead: first a lookup-table learner (a Q-table) on a tiny made-up "
     "traffic model, then the same idea on the real simulator, then the neural network, with a test for every piece. The neural network's "
     "learning step (backpropagation) was the part I was least sure how to write, so I checked it against a numerical test that compares the "
     "network's gradients with slow, simple estimates. It passed, and from then on I trusted it. Result: every later failure could be traced "
     "to the traffic or the settings, not to the code."),
    ("Problem 2: ", "The agent cheated.",
     "The first agent's score looked fine, but it was flipping the light at every decision, about 450 switches in a 30-minute run. It had "
     "found a loophole: I charged the cost per decision, and a switch (with its yellow light) lasts about 4 seconds, so flipping hid the "
     "jam. I could not have seen this from the score alone; I saw it only because I counted the switches. I changed the cost to be charged "
     "every simulated second, yellow included, and wrote a test that compares a flip-always policy with a hold policy. Result: the cheat "
     "disappeared, and I now always watch what the agent does as well as its score."),
    ("Problem 3: ", "My numbers hid the congestion.",
     "Each approach road holds only about 12 vehicles, so under heavy demand the extra cars wait outside the simulation. The queue length "
     "stayed flat while the delay grew, so a controller could look good while the junction was jammed. I added a measure for those held-back "
     "vehicles (the backlog) and now rank controllers by vehicles waiting (queue plus backlog). Result: the measure finally agreed with what "
     "I could see in the simulator."),
    ("Problem 4: ", "A good result that was partly luck.",
     "If you train many versions and keep the best, the best one may simply have been lucky on the traffic it was picked on. For example, my "
     "best rush-hour agent scored 116.2 on the traffic used to pick it and 122.2 on fresh traffic. I learned to use three separate sets of "
     "random traffic (seeds): one for training, one for tuning and picking, and one used only for the final test. Result: every number in "
     "this report is from the final-test traffic, so it is not flattered by the choosing."),
    ("Problem 5: ", "The agent worked on one traffic pattern only.",
     "My first good agent was trained on tidal traffic (heavy one way, then the other) and beat the fixed timer there: 9.9 vehicles waiting "
     "against 115. I thought the project was nearly finished. Then I tested it on rush hour and light traffic, and it lost: 198.5 against "
     "139.7, and 24.8 against 1.5. Training on a mix of patterns fixed light traffic. Rush hour improved only after I changed one setting, "
     "the discount factor, which controls how far ahead the agent looks: raising it from 0.95 to 0.99 made the agent value the later benefit "
     "of switching. Result: rush-hour waiting fell from about 200 to about 140, and different training runs started to agree with each other."),
    ("Problem 6: ", "A simple method beat my agent, and a better way of training fixed it.",
     "So far I had compared only with a fixed timer. That is easy to beat on uneven traffic, so I asked what a simple controller that does "
     "not learn would do. I wrote one, the reference rule: it counts the vehicles in each street and gives green to the busier one. My first "
     "version counted only stopped vehicles. A street with green has moving vehicles, so the rule saw almost nothing and switched at once, "
     "and it lost to the fixed timer by 12% to 131%. I noticed because changing its settings did nothing. I rewrote it to count all vehicles "
     "and chose its settings on separate seeds. Then it beat every early version of my agent: on tidal traffic 7.2 against 10.1 for my best "
     "agent, and on rush hour 126.6 against 139.8. My agent's training was also unstable: good early, worse later. I tried giving it the same "
     "vehicle counts, Double DQN (van Hasselt et al., 2016), slower updates of its target network, gradient clipping, a shrinking learning "
     "rate and the rule's experience in its memory, with only partial success (2 of 4 runs stayed good on tidal). What worked was learning "
     "from demonstrations (Hester et al., 2018): I show the agent the reference rule's decisions first, keep them in a memory that is never "
     "overwritten, and add a rule that stops the network drifting away from them. Result: every one of 16 runs on tidal and rush hour ended "
     "at or below the reference rule on the tuning traffic, and on fresh traffic the agents matched it. In heavy, uneven traffic 3 of 12 "
     "agents were significantly better than the rule (5% to 11%), but 2 were worse. Because the agents start from the rule, matching it is "
     "expected; the interesting cases are where they went beyond it."),
    ("Problem 7: ", "My first Kathmandu-style traffic made every controller look the same.",
     "I wanted the traffic to look like Kathmandu: mostly motorcycles, some buses, and vehicles turning. At 900 and 1,100 vehicles per hour "
     "per road, nothing I tried made a difference: the junction passed only about 1,800 vehicles an hour in total, and the reference rule "
     "behaved exactly like the fixed timer. I ran two extra tests to find out why. They showed that the turning vehicles, not the mixed "
     "fleet, halve a single lane's capacity: cars going straight passed 3,025 vehicles an hour, the mixed fleet going straight 3,232, and "
     "cars with turns 1,650. I recalibrated the demand to the measured capacity. Result: the traffic is now something a controller can "
     "affect. The vehicle mix (62% motorcycles, 22% cars, 8% buses, 8% light goods) is an assumption that I still have to check against its "
     "source."),
    ("Problem 8: ", "One model for every traffic pattern did not work.",
     "I wanted a single agent that handles any traffic, so I trained one on twelve random patterns. On three patterns it had never seen, it "
     "did not match the reference rule (rush hour 128 to 145 against 126.6, and worse on light traffic). In all four runs the best version "
     "was the one right after copying the rule, so further training added nothing. I do not know why, and any explanation would be a "
     "guess. Result: I report it as a negative result and keep one specialist agent per traffic pattern."),
]
anchor = heading._p
for lead, title, body in problems:
    anchor = clone_after(anchor, TPL_TITLE, lead, title)._p
    anchor = clone_after(anchor, TPL_PROBLEM_BODY, body)._p
for el in old:
    el.getparent().remove(el)

set_runs(find("Objective O4:"), "Objective 4: ", "Results against my target.")
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
anchor = res._p
for fname, caption in (("final_results.png", "Figure 1: Each dot is one independently trained agent, compared with the reference rule "
                                              "(changes beyond 30% are drawn at the edge)"),
                       ("regime_map.png", "Figure 2: Where the reference rule helps against a fixed timer, by demand level and unevenness "
                                          "(30 episodes per cell)")):
    pic_par = d.add_paragraph()
    pic_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic_par.add_run().add_picture(os.path.join(ROOT, "figures", "report", fname), width=Cm(13.5))
    anchor.addnext(pic_par._p)
    anchor = clone_after(pic_par._p, TPL_FIGCAP, caption)._p

# ---------------------------------------------------------------- 5-8
set_runs(find("Technical skills I gained"),
         "Technical skills I gained, with evidence in the repository: configuring SUMO and controlling it with TraCI (its remote-control "
         "interface); tabular Q-learning and DQN, including Double DQN and learning from demonstrations; a neural network with backpropagation "
         "written in NumPy and verified against a numerical gradient; experiment design with separate training, selection and test seeds and a "
         "decision rule fixed in advance; statistics for comparing controllers (confidence intervals, Welch and paired t-tests, effect size) "
         "written without a statistics library; building an installable, config-driven Python package with a command-line tool and plots; and "
         "testing code that talks to a simulator by using a fake interface.")
s = find("Strengths:")
if "I started the literature review late" in s.text:
    set_runs(s, s.text.replace("I started the literature review late", "I started the literature review late and it still needs critical synthesis"))

fill_rows(table_after("Table 3:"), [
    ["Action", "Due", "Done when"],
    ["Write up the comparative analysis (tables, figures, statistics)", "Week 9", "Results chapter drafted from the saved results"],
    ["Rewrite the literature review with critical synthesis (comparison table, where studies disagree, link to my results)", "Weeks 8–9", "Draft sent to my supervisor"],
    ["Write the final report (methods, results, discussion, conclusion)", "Weeks 9–10", "Complete draft reviewed by my supervisor"],
    ["Check the sources I rely on: Hester et al. (2018), van Hasselt et al. (2016), the vehicle-mix source", "Week 9", "Each checked against the original and the text corrected"],
    ["Fix the survey figures in the contextual report", "Week 9", "Figures labelled as real responses; form matches the appendix"],
])
set_runs(find("I will keep the plan current"),
         "I will keep the plan current by updating the README checklist whenever I finish a milestone and by reviewing this table at each "
         "weekly supervisor meeting.")

set_runs(find("Chapter 1:"), "Chapter 1: Introduction. ",
         "Problem and motivation; aim and objectives; the artefact (package and command line); structure of the report.")
set_runs(find("Chapter 2:"), "Chapter 2: Background and literature review. ",
         "Fixed-time and vehicle-actuated control (and the reported Lalitpur pilot, whose method is not published); reinforcement learning "
         "(Q-learning, DQN, Double DQN, learning from demonstrations); related work on RL for signal control, read critically; SUMO and TraCI; "
         "the gap this project addresses.")
set_runs(find("Chapter 4:"), "Chapter 4: Artefact design. ",
         "Architecture of the package; state, action and reward design; network architecture; scenario and config design; rejected options "
         "(PyTorch, per-second decisions, queue-only metric).")
set_runs(find("Chapter 6:"), "Chapter 6: Results. ",
         "Each target with how it was measured: the fair comparison of fixed timer, reference rule and DQN over 100 fresh-seed runs; the regime "
         "map over 16 demand patterns; specialist agents, Kathmandu-style traffic and the single-model experiment; training stability and the "
         "effect of learning from demonstrations.")
set_runs(find("Chapter 7:"), "Chapter 7: Evaluation. ",
         "Results against the objectives and the literature; limitations (one junction with one lane per road, an assumed vehicle mix, one "
         "model per scenario, seed sensitivity); project management.")
set_runs(find("Chapter 8:"), "Chapter 8: Conclusions and further work. ",
         "Summary; further work (multi-lane junctions with motorcycle filtering, real traffic counts, one general model, several junctions); "
         "personal reflection.")

set_runs(find("The build is ahead of plan"),
         "Up to Week 8 the build is complete and the core objectives are met: a SUMO junction, a hand-written network and DQN, and a fair "
         "comparison with a fixed timer. Adaptive control, learned or rule-based, clearly beats a fixed timer wherever the traffic gives it "
         "something to work with: about 94% less waiting on commute-style traffic and about 10% on a busy evening rush. A very simple "
         "reference rule that counts vehicles gets almost all of that benefit. The learned controller, trained from the rule's demonstrations, "
         "matches the rule and sometimes beats it by about 10% in heavy, uneven traffic, but not reliably, and I do not yet have one model for "
         "every pattern. The main lessons are to choose the comparison carefully, to look at behaviour as well as score, to test on traffic I "
         "did not choose from, and to report mixed results plainly. I will follow the action plan above, starting with the written "
         "comparative analysis and the literature review.")

# ---------------------------------------------------------------- references (details to be checked by the student)
lopez = find("Lopez, P.A.")
clone_after(lopez._p.getprevious(), TPL_REF,
            "Hester, T. et al. (2018) ‘Deep Q-learning from demonstrations’, Proceedings of the AAAI Conference on Artificial Intelligence, "
            "32(1). [check the details against the original before submitting]")
mnih = find("Mnih, V.")
clone_after(mnih._p, TPL_REF,
            "Onlinekhabar (2024) Nepal's first intelligent traffic lights operational from Kupondole to Jawalakhel. Available at: "
            "https://english.onlinekhabar.com/nepals-first-intelligent-traffic-lights-operational-from-kupondole-to-jawalakhel.html "
            "(Accessed: [add date]).")
last = find("SUMO Documentation")
clone_after(last._p, TPL_REF,
            "van Hasselt, H., Guez, A. and Silver, D. (2016) ‘Deep reinforcement learning with double Q-learning’, Proceedings of the AAAI "
            "Conference on Artificial Intelligence, 30(1). [check the details against the original before submitting]")

# wording sweep: things that must not appear in this version of the report
for p in d.paragraphs:
    for word in ("demo", "Demo", "Mac ", "Windows", "laptop", "density", "tuned rule", "Streamlit", "second computer"):
        if word in p.text:
            print("check wording:", repr(word), "|", p.text[:100])

d.save(PATH)
print("saved", PATH)
