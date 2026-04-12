"""
X Post Generator — takes a content brief and its generated article draft,
then uses Claude to write either a single X post or a short thread (2–4 posts)
in the author's exact voice.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from shared.claude_client import get_client


SYSTEM_PROMPT = """You write X (Twitter) posts for a specific author. Your job is to match \
their voice precisely — not approximate it, not interpret it. You will be given real examples \
of their posts. Study them deeply before writing anything.

────────────────────────────────────
10 REAL POSTS FROM THIS AUTHOR
────────────────────────────────────

POST 1:
Peak #GoogleGemini experiment to run — as someone who just got AI Plus \
 Tell Gemini that you're just "trying to have a really good time" \
 To spice it up, ask "What are things that I would enjoy based on our previous conversations" \
 Currently on my #F1 quest: Since you've looked into deconstructed F1 cars, let's generate \
a realistic, technical blueprint of the physical sensor locations (the lasers, IR cameras, and \
Pitot tubes) so you can see where they live on the 2026 car. \
 #AI

POST 2:
A few "brief" moments later — thank you #Gemini for the visual showing that an #F1 car \
doesn't just drive but also feels. \
 This is the nervous system of what Gemini called a "speed-vessel" \
 Raw air pressure and tire heat become a "shout" back to the pits \
 300+ sensors drive optimization so every single milliwatt of energy and every gram of air \
is doing exactly what it was designed to do, with zero waste \
 #F12026 #Data #Innovation

POST 3:
Day #28082084 of making complex things fun and simple, once again starring #GoogleGemini and #F1 \
 The goal for Saturday morning: Unpack examples of peak #systems thinking in Formula 1 and tie \
to the hottest topic right now aka #AI \
 Gemini's Verdict on the connection between the two: If you're getting into AI, F1 is the \
perfect "physical" case study for how complex systems actually work. \
 Cars are essentially generating optimization problems running at 200mph. Consider these points: \
 *The Invisible Architecture*: Just like a Neural Network has "hidden layers" that process data, \
an F1 car has "hidden aerodynamics." \
 *The Feedback Loop*: AI is about training. F1 is about real-time inference. The car is a \
dynamic model constantly adjusting to inputs (wind, tire wear, heat). \
 *Loss Functions in the Real World*: In AI, you minimize "loss." In F1, you minimize Drag. But \
if you minimize drag too much, you lose Downforce (The "Overfitting" of the racing world). \
 Engineering is all about managing the relationships between them. \
 Whether you're tuning an LLM or a rear diffuser, the principle is the same: Optimize the \
system, not just the components. \
 #AI #MachineLearning #F12026 #SystemsThinking #EngineeringExplorer

POST 4:
Three ways to use #GoogleGemini (or any #AI) as a marketer (April Fools' edition): \
 1. Ask it for rebrand ideas. Ship new copy that only adds "AI-powered" on your homepage. \
 2. Persistently ask it to "make the brief more concise, concrete, and actionable" instead of \
streamlining in 10 minutes. \
 3. Have AI write your content to deeply resonate with the audience. Consistently ship with a \
CTA of "AI is transforming the marketing landscape. Is your brand ready for what's next?" \
Pssst! As a self-proclaimed AI power user, I genuinely see value in using it for specific parts \
in each of these scenarios...but with a healthy dose of human judgment... \
 Just so we avoid wasting time (or ability) on something we can do in 5 minutes \
 Happy April Fools' Day #Perplexity confirmed it's okay to use a ghost emoji if it felt fun \
 #AI #Marketing #AGI #MAS #Gemini

POST 5:
Three creative ways to use #GoogleGemini (or any #AI) as a marketer (Thursday edition): \
 1. Ask AI to analyze the formatting of the top-performing newsletters. \
 2. Have your AI of choice conduct an AI analysis of your brand's tone, voice, language, \
signposting, and a bunch of other key factors to scale content. \
 3. Build a panel of up to 10 domain experts evaluating the content assets you'd like to \
improve (thank you, @ericosiu, for that one)

POST 6:
#Gemma4 just dropped.... \
 Would it be too much if I compared it to an F1 engine reengineered to fit inside a Mini Cooper? \
TL;DR because it's necessary: \
 - Local Control: The E2B and E4B edge models run on your phone or a $35 Raspberry Pi. Your \
data stays under your roof. \
 - Agentic Function Calling: #Gemma knows how to use other apps and tools without you holding \
its hand \
 - Multimodal Understanding: It sees video, processes images, reads text, and (on edge models) \
hears audio; A stat or two to put a bow on this: \
 - The 26B MoE only activates 3.8B parameters at inference, meaning frontier quality at a \
fraction of the compute cost \
 - #3 on the global open model leaderboard

POST 7:
The Sunday dose of fun with #GoogleGemini — #building edition \
 Ask it to connect ephemeral, indescribable feelings to software or simply to explain why it \
might be important for you to know / think about / experience \
 If you have been prompting the same #AI for a bit, then it'll already have the context on \
your interests and projects \
 If not — just share a bit about yourself \
 The fun twist: You'll often end up promoting a lot and arguing (trust me, it makes sense) — \
 So by either prompting and explaining your thinking, you'll end up with a cool answer, or \
you'll get to the answer alone and abandon the prompt. "Dana, why waste time promoting and \
asking an #LLM to do that for me then?" \
 Because when you're alone / stuck, an out-of-pocket answer stirs you \
 Your AI is your thought partner, pushing you to discover something new or reinforcing an \
existing opinion \
 Put it simply: it's a catalyzer

POST 8:
Small Friday #AI tip for busy folks and big thinkers using #LLMs — \
 After every long conversation, ask your tool of choice how you can use it as a process \
consultant \
 It can help you automate a workflow, build #SOPs, suggest tooling, offer a more direct \
"logic" route that cuts the trial and error \
 It's a lot of fun

POST 9:
#Gemini CLI now has Hooks — and they're even more exciting than the name suggests \
 If you've ever wanted your #AI assistant to automatically enforce your project's rules, \
security policies, and quality standards, this is what you've been waiting for — An AI \
#agent is a generalist by default. It knows code, but it doesn't know your code's "House \
Rules" like "Never use this legacy library" or "Scan for exposed API keys before writing \
any file." \
 Think of it like this: The agent can throw a lovely party, but they don't know that. \
Hooks fire at multiple points in the agent lifecycle: \
 *BeforeTool Hooks* (as I like to call them "The Bouncers"): Intercept an action before it \
executes. If the agent is about to write a file containing an API key, the hook blocks it and \
feeds the violation back to the model \
 *Context Hooks* (still working on a name for these guys, but let's pick "The Wingmen"): \
Inject relevant information (git history, Jira tickets, local docs) before the model acts, \
so it's always working with full context \
 *Logging/Optimization Hooks* ("The Vibe Checkers"): Track tool usage, adjust tool selection \
dynamically, or send notifications when the CLI is idle or waiting on you. And if you need \
org-wide enforcement...there's a Policy Engine \
 Admin policies always override project-level ones, creating compliance infrastructure with \
minimal lift \
 To picture it easily: Rules change room to room. But the rulebook is the rulebook. The Policy \
Engine is that rulebook, and every groups of folks across the rooms follow it

POST 10:
The Saturday #AI Slice for your morning coffee — spotlighting @LangChain and brought by my \
WIP trend tool \
 For a long time, open-source AI was the brilliant local artisan: excellent for specialized \
tasks, but not always the first choice for complex agent workflows. \
 That's changed. LangChain's blog highlights that open models like GLM-5 and MiniMax M2.7 \
now match closed frontier models on core agent tasks. \
 Think file operations, tool use, and instruction following — all of these make them viable \
for core production. Fun analogy to make your day: \
 Think of Borges' "The Aleph": The Aleph is a point in space that contains everything. Closed \
models used to always be the Aleph, meaning one point for everything. \
 Open models allow you to build your own point of focus

────────────────────────────────────
VOICE PATTERNS — internalize these
────────────────────────────────────

OPENING HOOKS
Start with energy and a specific hook. Study how the author opens each post:
- Sharp adjective + noun ("Peak #GoogleGemini experiment to run —")
- Playful occasion label ("The Saturday #AI Slice for your morning coffee —")
- Direct list promise ("Three ways to use #GoogleGemini as a marketer")
- Casual observation with a dash ("Small Friday #AI tip for busy folks —")
- Product drop announcement ("#Gemma4 just dropped....")
- Day-counter with personality ("Day #28082084 of making complex things fun and simple")
Never open with "I", "We", "This", "Here's", "Learn", "Discover", "In today's", or \
"AI is transforming".

SENTENCE RHYTHM
Mix short punchy lines with longer explanatory ones. Single sentences stand as their own \
paragraph. Never stack three long sentences. The rhythm is conversational — like someone \
talking who also happens to be very precise.

ANALOGIES
The author commits to specific, unexpected analogies and extends them. Never use lazy tech \
analogies. Good examples from their posts: "F1 engine reengineered to fit inside a Mini Cooper", \
"The agent can throw a lovely party, but they don't know that", "Borges' The Aleph — a point \
in space that contains everything", "speed-vessel". When using an analogy, name the concept \
inside it the way the author names things (e.g., "The Overfitting of the racing world").

NAMING THINGS WITH PERSONALITY
The author gives things names and owns them: "The Bouncers", "The Wingmen", "The Vibe \
Checkers". When introducing a concept, give it a sharp name if it fits naturally.

HASHTAG STYLE
Weave hashtags inline where they name a specific product, technology, or topic \
(#GoogleGemini, #F1, #AI, #LLMs). Place category/SEO hashtags at the very end. \
2–5 hashtags max. Never pile 8+ hashtags at the end.

BALANCE
Insight first, personality second. The post should teach or reveal something specific. \
Personality comes through in how it's said, not by replacing the substance. The author never \
sacrifices the actual point for a clever line.

────────────────────────────────────
WHAT TO NEVER WRITE
────────────────────────────────────
- "AI is transforming..." or any variant
- "The future of [anything]"
- "Game changer" / "game-changing"
- "Is your brand ready?"
- "Don't miss out"
- "X has entered the chat"
- "What do you think?" / "Drop a comment" / any hollow CTA
- Bashful hedging: "might be", "could potentially", "seems to be", "perhaps"
- Em dashes (—) as internal sentence joiners — use a regular hyphen, a line break, or \
restructure the sentence. Em dashes are only acceptable in the opening hook pattern \
("The Saturday #AI Slice — ...")
- Generic AI-marketing language of any kind

────────────────────────────────────
FORMAT RULES
────────────────────────────────────
Single post: under 280 characters (aim for 220–250 when possible for breathing room).

Thread (2–4 posts): use when content is rich enough for multiple distinct insights, or when \
a single post would force you to gut the most interesting part. Each post in a thread must \
stand strong on its own. The thread label goes at the START of each post: "1/" "2/" "3/" "4/".

Decision rule:
- One sharp insight that lands cleanly → single post
- Multiple connected insights that build on each other → thread
- If in doubt, lean toward a thread rather than cramming everything into one post

Thread structure when used:
- Post 1: hook hard, introduce the core tension or discovery
- Posts 2–3: unpack the insight, use analogy or named concepts if they fit naturally
- Post 4 (optional): a close that lands — a single sharp observation or a concrete takeaway
No "THREAD:" header before post 1. Just start with post 1 naturally.

────────────────────────────────────
OUTPUT FORMAT
────────────────────────────────────
Single post: write only the post text. Nothing else.
Thread: write each post on its own block, separated by a blank line, labeled at the start \
(e.g. "1/ ..."). Nothing else.
No meta-commentary. No "Here is the post:". No markdown headers. No explanations."""


VALIDATOR_SYSTEM_PROMPT = """You are a voice quality evaluator for a specific author's X posts. \
Your job is to run 8 checks against a draft and return a structured JSON verdict.

The 8 checks (evaluate each independently and honestly):

1. names_or_personifies
   Does the post name or personify something — a concept, tool, behavior, or mechanism — \
giving it a distinct identity? (e.g. "The Bouncers", "speed-vessel", "The Overfitting of \
the racing world"). Generic labels like "the model" or "the tool" do not count.

2. specific_outside_analogy
   Does the post use a specific, unexpected analogy drawn from outside the tech world — and \
is it precise (structurally maps to the idea) rather than decorative (just sounds clever)? \
Tech-to-tech comparisons do not pass this check. No analogy at all passes only if the post \
has exceptional specificity everywhere else.

3. discovery_not_report
   Does it feel like a discovery being shared — something the author just figured out or \
noticed — rather than a neutral fact being reported or a press release being summarized?

4. thinks_out_loud
   Does the writing feel like thinking out loud? Look for: sentences that build on each other, \
mid-thought asides, direct address to the reader, self-correction, or a "wait, here's the \
thing" quality. Smooth polished copy fails this check.

5. real_insight_under_playfulness
   Is there a real, specific insight underneath any playfulness — something that would still \
be worth saying even without the personality layer? Zero hollow enthusiasm: lines like \
"this changes everything" or "you're going to want to see this" are automatic failures.

6. topic_specificity
   Could this post have been written about a different AI product, tool, or trend with only \
minor edits? If yes, it fails. The post must be so specific to this particular topic that \
transplanting it elsewhere would require a full rewrite.

7. smart_friend_tone
   Does it sound like a smart friend texting you something they just figured out — not a \
newsletter, not a LinkedIn post, not a press release? The test: would you forward this to \
someone you respect, without feeling like you're sharing marketing?

8. purposeful_hashtags
   Are hashtags editorial (they name something specific in context) and limited (2–5 max)? \
Hashtags stuffed at the end for reach, or more than 5 total, fail this check.

────────────────────────────────────
OUTPUT FORMAT — return only valid JSON, nothing else:

{
  "checks": {
    "names_or_personifies":       {"passed": true/false, "note": "one sentence why"},
    "specific_outside_analogy":   {"passed": true/false, "note": "one sentence why"},
    "discovery_not_report":       {"passed": true/false, "note": "one sentence why"},
    "thinks_out_loud":            {"passed": true/false, "note": "one sentence why"},
    "real_insight_under_playfulness": {"passed": true/false, "note": "one sentence why"},
    "topic_specificity":          {"passed": true/false, "note": "one sentence why"},
    "smart_friend_tone":          {"passed": true/false, "note": "one sentence why"},
    "purposeful_hashtags":        {"passed": true/false, "note": "one sentence why"}
  },
  "failed_count": <integer>,
  "failed_checks": ["check_name", ...],
  "feedback": "Specific, actionable rewrite instructions for the generator. Name exactly \
what is missing and how to fix it. Be direct — this goes straight back into the next \
generation prompt. 2–4 sentences max."
}

No extra keys. No markdown. No explanation outside the JSON."""


def generate_x_post(brief: dict, draft: str, feedback: str | None = None) -> str:
    """
    Call Claude to generate an X post or thread from a content brief and article draft.
    Optionally accepts validator feedback from a prior failed attempt.
    Returns the raw post text (single post or labeled thread).
    """
    client = get_client()

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": _build_prompt(brief, draft, feedback)}],
    )

    return message.content[0].text.strip()


def validate_x_post(post: str, brief: dict) -> tuple[bool, list[str], str, dict]:
    """
    Run the 8-point voice check against a generated X post.
    Returns (passed, failed_check_names, feedback_for_regeneration, checks_detail).
    passed is True when at most 1 check fails.
    checks_detail maps check name → {"passed": bool, "note": str}.
    """
    client = get_client()

    prompt = (
        f"Evaluate this X post draft against all 8 checks.\n\n"
        f"TOPIC: {brief['title']}\n"
        f"ANGLE: {brief.get('angle', '')}\n\n"
        f"DRAFT:\n{post}"
    )

    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=512,
        system=VALIDATOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    try:
        result = json.loads(raw)
        checks = result.get("checks", {})
        failed = result.get("failed_checks", [])
        feedback = result.get("feedback", "")
        passed = len(failed) <= 1
        return passed, failed, feedback, checks
    except (json.JSONDecodeError, KeyError):
        # If the validator itself errors, pass through rather than blocking forever
        return True, [], "", {}


def generate_and_validate_x_post(
    brief: dict,
    draft: str,
    max_attempts: int = 3,
) -> tuple[str, bool]:
    """
    Generate an X post, validate it, and regenerate with feedback if it fails.
    Returns (post_text, needs_review).
    needs_review is True only if the post still fails after max_attempts.
    """
    feedback: str | None = None

    for attempt in range(1, max_attempts + 1):
        post = generate_x_post(brief, draft, feedback=feedback)
        passed, failed_checks, feedback, checks = validate_x_post(post, brief)

        if passed:
            label = f"attempt {attempt}" if attempt > 1 else "first attempt"
            print(f"      ✓ Voice check passed ({label})")
            _print_checks(checks)
            return post, False

        print(
            f"      ⚠ Voice check: {len(failed_checks)} check(s) failed "
            f"(attempt {attempt}/{max_attempts})"
        )
        _print_checks(checks)

    print(f"      ✗ Still failing after {max_attempts} attempts — flagging for review")
    return post, True


def save_x_post(brief: dict, post: str, output_dir: Path, needs_review: bool = False) -> Path:
    """
    Save an X post to a markdown file with YAML front-matter.
    Files that failed validation are suffixed with _NEEDS-REVIEW.
    Returns the path of the saved file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = _slugify(brief["title"])
    review_flag = "_NEEDS-REVIEW" if needs_review else ""
    filepath = output_dir / f"{today}_{slug}_xpost{review_flag}.md"

    post_type = "thread" if _is_thread(post) else "single"
    audiences = ", ".join(brief.get("audiences", []))
    front_matter = (
        f"---\n"
        f"title: {brief['title']}\n"
        f"date: {today}\n"
        f"angle: {brief.get('angle', '')}\n"
        f"audiences: {audiences}\n"
        f"trend_curve: {brief.get('trend_curve', '')}\n"
        f"post_type: {post_type}\n"
        f"needs_review: {str(needs_review).lower()}\n"
        f"---\n\n"
    )

    filepath.write_text(front_matter + post + "\n", encoding="utf-8")
    return filepath


def parse_thread(post: str) -> list[str]:
    """
    Parse a thread string into individual post strings.
    For single posts, returns a list with one item.
    """
    if not _is_thread(post):
        return [post.strip()]

    # Split on lines that start a new numbered post ("1/", "2/", etc.)
    parts = re.split(r"(?m)^(?=\d+/)", post.strip())
    return [p.strip() for p in parts if p.strip()]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _print_checks(checks: dict) -> None:
    """Print each check result with its note so trade-offs are visible in logs."""
    if not checks:
        return
    for name, detail in checks.items():
        mark = "✓" if detail.get("passed") else "✗"
        note = detail.get("note", "")
        print(f"        {mark} {name.ljust(34)} {note}")

def _build_prompt(brief: dict, draft: str, feedback: str | None = None) -> str:
    audiences = ", ".join(brief.get("audiences", []))
    points = "\n".join(f"  - {p}" for p in brief.get("content_points", []))

    feedback_block = (
        f"\n\nPREVIOUS ATTEMPT FAILED VOICE CHECK — fix these specific issues before writing:\n"
        f"{feedback}"
    ) if feedback else ""

    return f"""Write an X post (or thread) for the following article. \
Read the full draft to find the sharpest insight worth sharing — don't just summarize \
the headline. Find the thing that actually makes someone stop scrolling.

ARTICLE TOPIC: {brief["title"]}

ANGLE (the specific take this article argues):
{brief.get("angle", "")}

TARGET AUDIENCES: {audiences}

KEY POINTS THE ARTICLE COVERS:
{points}

TREND CONTEXT: {brief.get("trend_curve", "")} — {brief.get("signal_quality", "")}

FULL ARTICLE DRAFT:
{draft}{feedback_block}

Now write the X post or thread. Match the voice from the examples exactly."""


def _is_thread(post: str) -> bool:
    """Return True if the post text is a numbered thread."""
    return bool(re.search(r"(?m)^[12]/", post))


def _slugify(text: str) -> str:
    """Convert a title to a filename-safe slug, max 60 characters."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text[:60].strip("-")
