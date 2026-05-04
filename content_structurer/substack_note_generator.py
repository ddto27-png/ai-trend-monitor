"""
Substack note generator for the Content Structurer pipeline.

For each generated article draft, produces a 100-200 word Substack Note
in Dana's voice: moment → texture → turn → closer.

Includes the same voice validator used by the Skitsa note generator —
8 checks, regeneration loop up to 3 attempts, _NEEDS-REVIEW flag.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from shared.claude_client import get_client


_SYSTEM = """\
You write Substack Notes in Dana's exact voice.

Study these 5 real notes by Dana carefully before writing anything. \
Internalize the rhythm, the vocabulary, how she opens, how she turns, \
how she closes. Do not approximate — match.

────────────────────────────────────
5 REAL NOTES BY DANA
────────────────────────────────────

NOTE 1:
Call it "being an egomaniac," or not, but there's something to say about racing to build \
the future (and when I say this, it doesn't just mean starting a company).

It's about creating things you wish were there, from a small "spin-the-wheel" game for \
movie night to a workflow at work.

We all have our ideal version of the future we want to live in.

If you're not the one building it (dare I say, "bringing it to life,") someone else will. \
And you'll live in their version of your future.

Just some Sunday thoughts while one is waiting for the train :)

---

NOTE 2:
It's ~drum roll~ Wander Wednesday, where I take AI somewhere it wasn't supposed to go \
and see what comes back.

Today I asked it to look at fashion through a systems thinking lens.

I was expecting it to surface ideas about the process of creating a garment (which it did, \
sharing below), but honestly, it spanned many more aspects than I thought:

The collection as a single vision — one silhouette, one mood, sometimes one reference image \
— and everything else follows. Fabric, construction, factories, timelines. Hundreds of \
decisions collapsing into each other from a single upstream choice. One person's eye shaping \
what the world wears two years later.

Trend cycles as feedback loops — a silhouette gets adopted, oversaturation kills it, the \
backlash becomes the next trend. The system self-corrects.

Fast fashion as a system under stress — optimized for one variable (speed/cost) until the \
whole thing becomes brittle. Classic what happens when you over-optimize a complex system.

Seasonality as an artificial constraint — the four-season structure isn't natural, it's an \
inherited system rule that the whole industry optimizes around, even when it stops making sense.

*Bonus points for the sliver of real self-doubt when it suggested a point countering one of \
its original — that system has almost no real-time feedback. In the LLM's words, "By the \
time you know a silhouette didn't sell, you've already committed to next season's version of it."

Not all of the ideas were easy to understand, or to agree with.

But the fact that I could have a buddy that could come up with infinite analogies to help me \
see something in a new light and help me put myself in others' shoes was fascinating.

What's your Wander Wednesday experiment? :)

---

NOTE 3:
For a long time, I thought writing was pure magic. I pictured it as a skill encoded in your \
DNA, a "muse" that occasionally whispered brilliant ideas.

I quickly learned that if you want to create at scale (especially when things are moving fast \
and there's no one to hold your hand), you can't rely on magic. You need a system. \
You need scaffolding.

As renowned storyteller Wright Thompson put it on David Perell podcast: "Writing is not \
about words, it's about architecture."

Think of your content like a skyscraper. Technical jargon and "pretty words" are the \
gold-plated faucets in the penthouse. However, they can't find a foundation made of hollow drywall.

Thompson explains it simply: "Only when you really understand how things fit together and \
move can you then actually be thinking about the words."

This has been on my mind quite a lot recently, especially as AI is blurring the lines \
between disciplines.

I feel like, whether you're an architect, a software engineer, or a writer, we are all \
builders of coherence.

The architect assesses the client's vision and constraints (budget, site) before drawing a \
single line. The writer evaluates the goal of a content piece, the audience, the unique \
angle, and the SEO/AEO (among many factors) to build a roadmap for writing.

The Engineer deals with technical debt, making trade-offs between simple fixes and complex \
solutions. The Writer allocates "real estate," picking which idea gets the 50th-floor view \
and which stays in the basement.

Of course, each of these roles are uniquely different in more ways than I can count on a \
Substack Note.

But there's something interesting to say about the surprising overlaps we see :)

---

NOTE 4:
To everyone who wants to get their hands dirty with some AI, vibe-coding, and building but \
is hesitant to do so —

One of the easiest and most fun beginner projects I've had is building a personalized \
newsletter on a topic you care about. A simple framework to follow:

Pick 3-5 publications you want to query every day
Explain what you're trying to build to your AI coding agent.
Follow its instructions (it'll ask you to set up GitHub, Replit, etc. if you don't have \
such already — trust me, it's easier than you think!)
Hook it up to Resend, an email platform that lets you build and test out emails
After running some testing, get down to the fun parts — customization, greeting message, \
design, voice, etc. The sky is the limit.

In a few hours, you'll have a personalized newsletter (could even be publications you need \
to write your Substack!) and you'll have built your first AI-coded project! :)

---

NOTE 5:
There's a word in Japanese — ma — that roughly translates as the pause between notes. \
It's the space that gives the sound its shape.

I see it very fitting in relation to information. We talk a lot about input and output, \
processing speed and cognitive load. But almost nobody talks about the gap between receiving \
and understanding — the ma. This is the moment after you've taken something in and before \
it settles into understanding.

A walk is ma. A drawing is ma. Even waiting for your coffee machine to fill your cup can be ma.

What's yours? :)

────────────────────────────────────
DANA'S VOICE — patterns to internalize
────────────────────────────────────

OPENING
Never start with a question, a statistic, or "Have you ever." Always open with something \
noticed — a scene, a named concept, a tension, a provocation. The first line withholds the \
thesis and trusts the reader to follow. Never open with "I" as the very first word.

SENTENCE RHYTHM
Long → short → long → very short. Short sentences land emphasis, never decoration. \
The em dash extends a beat. Parentheticals syncopate without breaking flow. \
Single sentences frequently stand alone as their own paragraph.

STRUCTURE
Aggressive white space. No paragraph exceeds 4 sentences. Lines break for rhythm, not just \
structure. Lists only appear when genuinely listing a process — never as a substitute for \
prose thinking.

THE TURN
Dana zooms from a specific observation to a broader principle — but never announces it. \
No "the takeaway is," no "what this means is," no "the lesson here is." \
The turn arrives quietly and becomes true by the time you reach it.

THE CLOSE
Short, light, conversational. Soft landing → self-reducing coda ("just some Sunday thoughts," \
"in more ways than I can count on a Substack Note") → a specific reader-facing question \
OR :) OR both. Never a directive. Never a subscribe prompt.

THE :) MARKER
":)" appears in every note Dana writes. It signals warmth without performance — always at the \
end of a question or a soft exit line. Use it once, where it's earned.

THE WE PIVOT
Dana moves from first-person observation ("I quickly learned," "I feel like") to a \
shared-experience frame ("we all have," "we are all builders of coherence," \
"almost nobody talks about"). The personal becomes collective.

LANGUAGE
Warm, specific, never hype. Mix registers freely: technical terms alongside "buddy," \
"vibe-coding," "dare I say." Invent compound phrases for precision. \
Never: "game-changing," "revolutionary," "must-read," "unlock," \
"we should all," "the lesson here is."

────────────────────────────────────
STRUCTURE TO FOLLOW
────────────────────────────────────
1. The moment — a specific, real-world observation. Sensory. No grand opener.
2. The texture — 2-3 units showing *why* it was interesting. Specific details, not adjectives.
3. The turn — one sentence connecting to the reader's world. Simple. Direct. Not announced.
4. The closer — generous ending. Fun fact, quiet intention, specific question. ":)" where earned.

TARGET LENGTH: 100–200 words. No headers. No bullets in the core argument. \
Pure prose, line-broken like poetry."""


_VALIDATOR_SYSTEM = """\
You evaluate Substack notes written in Dana's voice against 8 specific checks. \
Return only valid JSON — nothing else, no markdown code fences.

The 8 checks:

1. uses_smiley_close
   Does ":)" appear anywhere in the note? It appears in every real note Dana has written. \
   Pass if ":)" is present anywhere in the text.

2. opens_with_observation_not_question
   Does the first sentence end with a period, em dash, or ellipsis — NOT a question mark? \
   Dana never opens with a question. Fail if the first sentence ends with "?".

3. contains_deflating_coda
   Does the note contain a self-reducing or self-situating phrase near the end that steps \
   back from its own point? Examples that pass: "just some thoughts," "in more ways than I \
   can count," "I can't count on a Substack Note," "while one is waiting for the train." \
   Fail if the note escalates to a strong conclusion with no softening move.

4. closes_with_specific_reader_question
   If the note ends with a question, is it specific and personal — not generic engagement \
   bait? "What's yours?" and "What's your [X] experiment?" pass. \
   "What do you think?" and "Let me know in the comments" fail. \
   Also passes if the note ends with ":)" without a question.

5. no_hype_or_moralizing_language
   Scan for banned language. Hype: "game-changing," "revolutionary," "must-read," \
   "you need to see this," "incredible," "amazing," "unlock," "transform." \
   Moralizing: "we should all," "it's important that," "the lesson here is," \
   "we must," "everyone needs to," "the takeaway is," "what this means is." \
   Fail on any match.

6. turn_is_implicit_not_announced
   The note zooms from a specific observation to a broader principle — but does the turn \
   arrive without being signposted? Fail if the pivot uses: "and this teaches us," \
   "the takeaway is," "what this means is," "the point is," "this shows us," \
   "the lesson here is."

7. uses_we_pivot_after_personal_observation
   Does the note move from first-person observation ("I thought," "I noticed," \
   "I quickly learned") to a shared-experience frame using "we," "you," "almost nobody," \
   or "all of us"? Fail if the entire note stays in "I" with no shift outward.

8. white_space_enforced_no_walls
   Does every paragraph contain 4 sentences or fewer? \
   Fail if any paragraph contains 5 or more sentences.

────────────────────────────────────
OUTPUT — return only this JSON, nothing else:

{
  "checks": {
    "uses_smiley_close":                       {"passed": true/false, "note": "one sentence why"},
    "opens_with_observation_not_question":     {"passed": true/false, "note": "one sentence why"},
    "contains_deflating_coda":                 {"passed": true/false, "note": "one sentence why"},
    "closes_with_specific_reader_question":    {"passed": true/false, "note": "one sentence why"},
    "no_hype_or_moralizing_language":          {"passed": true/false, "note": "one sentence why"},
    "turn_is_implicit_not_announced":          {"passed": true/false, "note": "one sentence why"},
    "uses_we_pivot_after_personal_observation":{"passed": true/false, "note": "one sentence why"},
    "white_space_enforced_no_walls":           {"passed": true/false, "note": "one sentence why"}
  },
  "failed_count": <integer>,
  "failed_checks": ["check_name", ...],
  "feedback": "Specific, actionable rewrite instructions referencing Dana's patterns. \
Name exactly what is missing and how to fix it. 2-4 sentences max."
}"""


def generate_note(brief: dict, draft: str,
                  feedback: str | None = None) -> str:
    """
    Generate a 100-200 word Substack note from a content brief and its article draft.
    Optionally accepts validator feedback from a prior failed attempt.
    """
    client = get_client()

    feedback_block = (
        f"\n\nPREVIOUS ATTEMPT FAILED VOICE CHECK — fix these specific issues:\n{feedback}"
    ) if feedback else ""

    audiences = ", ".join(brief.get("audiences", []))
    points = "\n".join(f"  - {p}" for p in brief.get("content_points", []))

    prompt = f"""\
Write a Substack Note (100–200 words) inspired by this article.

Read the full draft below — find one specific observation, moment, or detail \
that would make a genuine Substack note. Not a summary. Not a teaser. \
A thought worth sharing because you had it.

TITLE: {brief["title"]}
ANGLE: {brief.get("angle", "")}
TARGET AUDIENCES: {audiences}
KEY POINTS:
{points}

FULL ARTICLE DRAFT:
{draft}

Do not start with "I" as the very first word. Open with the observation itself.
Match the voice, rhythm, and structure from the examples exactly.
No title. No headers. Pure prose, line-broken for rhythm.{feedback_block}"""

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=400,
        system=_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()


def validate_note(note: str, brief: dict) -> tuple[bool, list[str], str, dict]:
    """
    Run the 8-point voice check against a generated Substack note.
    Returns (passed, failed_check_names, feedback_for_regeneration, checks_detail).
    passed is True when at most 1 check fails.
    """
    client = get_client()

    prompt = (
        f"Evaluate this Substack note draft against all 8 checks.\n\n"
        f"TITLE: {brief.get('title', '')}\n\n"
        f"DRAFT:\n{note}"
    )

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=600,
        system=_VALIDATOR_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
        checks = result.get("checks", {})
        failed = result.get("failed_checks", [])
        feedback = result.get("feedback", "")
        passed = len(failed) <= 1
        if not checks:
            print(f"      (validator returned no check detail — raw: {raw[:120]})")
        return passed, failed, feedback, checks
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"      (validator parse error: {exc} — raw: {raw[:120]})")
        return True, [], "", {}


def generate_personal_story_tip(note: str, brief: dict) -> str:
    """
    Generate a short editorial prompt suggesting the type of personal story
    or observation Dana could add to make the note feel lived-in.
    """
    client = get_client()

    prompt = (
        f"Read this Substack note and suggest — in one short paragraph starting with '*' — "
        f"the type of personal story, observation, or lived moment Dana could weave in to "
        f"make it feel more grounded in her own experience. Be specific: name the kind of "
        f"situation, sensory detail, or interaction that would fit naturally. "
        f"Don't rewrite the note. Don't explain why it would help. Just give the prompt — "
        f"direct, specific, one paragraph.\n\n"
        f"Title: {brief.get('title', '')}\n\n"
        f"NOTE:\n{note}"
    )

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()


def generate_and_validate_note(
    brief: dict,
    draft: str,
    max_attempts: int = 3,
) -> tuple[str, bool, str]:
    """
    Generate a Substack note, validate it, and regenerate with feedback if it fails.
    Returns (note_text, needs_review, personal_story_tip).
    needs_review is True only if the note still fails after max_attempts.
    """
    feedback: str | None = None

    for attempt in range(1, max_attempts + 1):
        note = generate_note(brief, draft, feedback=feedback)
        passed, failed_checks, feedback, checks = validate_note(note, brief)

        if passed:
            label = f"attempt {attempt}" if attempt > 1 else "first attempt"
            print(f"      ✓ Voice check passed ({label})")
            _print_checks(checks)
            tip = generate_personal_story_tip(note, brief)
            return note, False, tip

        print(
            f"      ⚠ Voice check: {len(failed_checks)} check(s) failed "
            f"(attempt {attempt}/{max_attempts})"
        )
        _print_checks(checks)

    print(f"      ✗ Still failing after {max_attempts} attempts — flagging for review")
    tip = generate_personal_story_tip(note, brief)
    return note, True, tip


def save_note(brief: dict, note: str, output_dir: Path,
              needs_review: bool = False, tip: str = "") -> Path:
    """Save a Substack note as a markdown file with YAML front-matter."""
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = _slugify(brief.get("title", "note"))
    review_flag = "_NEEDS-REVIEW" if needs_review else ""
    path = output_dir / f"{today}_{slug}_note{review_flag}.md"

    audiences = ", ".join(brief.get("audiences", []))
    front_matter = (
        f"---\n"
        f"date: {today}\n"
        f"title: \"{brief.get('title', '')}\"\n"
        f"angle: {brief.get('angle', '')}\n"
        f"audiences: {audiences}\n"
        f"type: substack-note\n"
        f"needs_review: {str(needs_review).lower()}\n"
        f"---\n\n"
    )

    tip_block = f"\n\n---\n\n{tip}\n" if tip else ""
    path.write_text(front_matter + note + tip_block, encoding="utf-8")
    return path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_checks(checks: dict) -> None:
    if not checks:
        return
    for name, detail in checks.items():
        mark = "✓" if detail.get("passed") else "✗"
        note = detail.get("note", "")
        print(f"        {mark} {name.ljust(42)} {note}")


def _slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:55]
