"""Mimi's discovery methodology, transcribed verbatim from the source documents.

Imported once into `methodology_modules` / `methodology_questions`; after that the
database is the source of truth and the advisor edits it at /admin/methodology.

Transcription rules: wording, punctuation, dashes, quote marks, duplicates and typos
are kept exactly as they appear in the source. Nothing here is paraphrased.

Structure: (module key, module title, family, suggested session, [(section heading, [questions])])

Module order and session groups follow the beta structure:
  Session 1: Purpose + Love · 2: Play + Work · 3: Service + Community · 4: Alignment + Evolution · 5: Review + Statement
The opening "Purpose" module is a beta addition, not part of Mimi's seven documents.
"""

OPENING_MODULE = (
    "purpose", "Purpose", "Beta opening", 1,
    [("", [
        "What is the purpose of your wealth?",
        "What does a meaningful life look like to you?",
    ])],
)

METHODOLOGY_SOURCE = [
    (
        "love", "Love", "Ikigai", 1,
        [
            ("What Lights You Up", [
                "What activities, topics, or experiences make time disappear for you — when you lose track of the clock without noticing?",
                "Is there something you loved as a younger person that has been crowded out by obligation or practicality — and that still pulls at you?",
                "When you imagine a day that felt genuinely good — not productive, not impressive, just good — what was in it?",
                "What’s been present in your life consistently across different chapters — not necessarily in the same form, but the same underlying quality?",
                "Which items on your list feel most like you — not aspirational versions – and which ones feel like they’re from someone you used to be or want to become?",
                "How much of your current week is organized around what you love, versus what you’re obligated to or known for?",
            ]),
            ("What You Return to Again and Again", [
                "What do you find yourself drawn to in your free time, across different chapters of your life?",
                "What topics, questions, or activities do you engage with without needing a reason?",
                "When you imagine a version of your life that feels deeply satisfying, what is happening in it that isn't happening now?",
                "Is there something on your list that your financial life currently doesn't make room for?",
                "What would it take to change that?",
            ]),
            ("When You Felt Most Fully Yourself", [
                "Think of two or three moments in your life when you felt most fully yourself. What were you doing, who were you with, and where were you?",
                "What do those moments have in common — about the kind of engagement, attention, or relationship involved?",
                "How frequently does your current life create the conditions for that quality of experience?",
                "Is there a version of yourself that appears in those moments who doesn’t show up much in your day-to-day financial and professional life?",
            ]),
            ("If Money Were Irrelevant", [
                "If you removed financial return as a criterion entirely, what would you spend your time doing?",
                "What activities make you forget to check the time — and when was the last time your pursued them?",
                "Is there something you once loved that you stopped doing because it didn't fit the shape of your current life? What was it?",
            ]),
        ],
    ),
    (
        "play", "Play", "Ikigai", 2,
        [
            ("What People Come To You For", [
                "What do people ask you for — advice, help, perspective, a skill, a conversation?",
                "What do you find yourself doing in a group that others don't seem to notice they're not doing?",
                "Is there something people thank you for that you barely registered as a contribution?",
            ]),
            ("What Comes Intuitively", [
                "What do you find yourself doing that other people seem to struggle with?",
                "When you're in flow — genuinely absorbed, time disappearing — what are you usually doing?",
                "Is there somewhere in your life where this natural ability is already showing up — and somewhere you've been keeping it separate from your financial or philanthropic decisions?",
            ]),
            ("What You Are Quietly Most Proud Of", [
                "What is one thing you have done in the last few years that you are quietly proud of — something that didn’t necessarily make the resume?",
                "What does this reveal about what you value, as distinct from what you’ve been encouraged to achieve?",
                "How much of your current life is structured to create more opportunities for this kind of experience?",
                "There is often a tension between what we’re proud of privately and what we’re rewarded for publicly. If your financial life were built around the former rather than the latter, what would that require you to reframe?",
            ]),
            ("Strengths Under Pressure", [
                "What capacities seem to sharpen for you when things are difficult, rather than diminishing? What are you able to do then that you cannot always access in calmer conditions?",
                "What do other people seem to recognize in you during difficult times that you sometimes overlook in yourself?",
                "Is there a kind of challenge that brings out a version of you that feels most like yourself — most present, most clear, most capable? What does that challenge look like?",
                "What do other people seem to recognize in you during difficult times that you sometimes overlook in yourself?",
            ]),
        ],
    ),
    (
        "work", "Work", "Ikigai", 2,
        [
            ("Where Purpose and Skill Meet", [
                "Can you recall a specific moment or period when work drew on a skill and felt meaningful at the same time? What were you doing, and what made it different?",
                "What skill was at the center of it — and was that skill something you developed intentionally, or was it intuitive?",
                "If you stripped away income and status from the equation — if the financial outcome were guaranteed — what skill would you still want to be using in the next chapter of your life?",
            ]),
            ("Congruence In How You Earn", [
                "When you describe your work to someone who doesn’t know you professionally, what do you lead with — and what do you leave out?",
                "Which parts of your vocation feel most consistent with your values — and which parts require a compartmentalization?",
                "Has the congruence between your work and your identity changed over time — and if so, what shifted?",
            ]),
            ("Where Your Work Life Has Drifted", [
                "Where in your professional life do you feel most like yourself — and where do you feel most like a version of yourself you agreed to become?",
                "What have you built professionally that you're genuinely proud of, apart from its financial return?",
                "Is there something you've been waiting for — permission, a number, an exit — before you let yourself want something different? What would it mean if that permission never came?",
            ]),
        ],
    ),
    (
        "service", "Service", "Ikigai", 3,
        [
            ("The Injustice You Cannot Look Away From", [
                "What is the problem in the world — local, national, or global — that you find yourself returning to most often? The one you can't scroll past.",
                "Where did your awareness of this problem begin? Was it personal, witnessed, or learned?",
                "If you imagine the version of yourself who does something meaningful about this — what does that look like, even roughly?",
            ]),
            ("What Would Be Meaningfully Different", [
                "If the work/service you're imagining worked exactly as you hope — what does the world, or one person's life, look like on the other side of it?",
                "What do you know — from direct experience or proximity — about what this problem actually requires? Where does your understanding come from?",
                "Imagine looking back from ten years out on the contribution you made. What do you most hope you'll be able to say actually changed?",
            ]),
            ("Whose Lives You Most Want Your Resources to Touch", [
                "Has there been a moment in your life when your resources — money, time, access — touched someone’s life in a way that stayed with you? What made it meaningful?",
                "Are the people you most want your wealth to reach the same people your wealth is currently supporting? Where is there alignment, and where is there a gap?",
                "Is there someone — a person, a type of person, a community — whose flourishing would feel, to you, like the truest measure of your life’s impact?",
                "Is there someone in your life — past or present — whose changed circumstances have already shown you what your resources can do?",
                "What would it mean to you personally to know that your wealth had touched that person’s life in a meaningful way?",
            ]),
        ],
    ),
    (
        "community", "Community", "Purpose", 3,
        [
            ("The 5 People Your Wealth Touches", [
                "Name five people whose lives are materially or emotionally shaped by your wealth. Who are they, and what is the nature of that connection?",
                "For each person, what does your wealth make possible for them — and what, if anything, does it complicate?",
                "Where in these relationships do you feel a sense of alignment between your intentions and your actual impact?",
                "Where do you sense an integrity gap — a place where the impact of your wealth on someone doesn’t match what you’d want it to be?",
                "What are your intentions behind the wealth you’ve allocated to the 5 individuals? What are your fears and desires?",
            ]),
            ("What Full Alignment Feels Like In Your Body", [
                "Can you recall a specific moment when you felt fully aligned in your contribution to a community you care about? What were you doing, and what community was it?",
                "How often does your current financial life create the conditions for that kind of community engagement — and how often does it pull you away from it?",
                "If your wealth were fully aligned with how you want to show up for those communities, what would be noticeably different about how you spend your time?",
            ]),
            ("What The People Closest To You Actually Need", [
                "Who are the two or three people you feel most responsible toward — financially, emotionally, or both? Name them specifically.",
                "For each person you named: what do you understand them to need from your wealth — and how do you know? Did they tell you, or have you assumed?",
                "Is there a difference between what they've asked for and what you believe would actually serve them? Where does that difference come from?",
                "What would it cost you — emotionally, structurally — to ask the people closest to you what they actually need, directly and without pre-framing the answer?",
            ]),
            ("Constrained Generosity – What You Would Donate More Of", [
                "What is one form of donating — of time, money, or attention — that you wish you were doing more of, but aren't?",
                "What is preventing you from contributing in your desired manner?",
                "What are the constraints and where do you think it comes from?",
                "What would one step forward in liberating yourself from those constraints look like?",
            ]),
        ],
    ),
    (
        "alignment", "Alignment", "Purpose", 4,
        [
            ("What A Fully Aligned Life Looks Like", [
                "Describe a version of your life — specific, not abstract — in which you feel fully aligned: your time, your energy, your relationships, and your resources all pointing in the same direction.",
                "What in your current life is already aligned in that way — already genuinely congruent with who you are?",
                "Where do you feel the clearest gap between how you’re living and how you sense you’re meant to be living?",
                "What role, if any, has your wealth played in creating or sustaining that gap — making it easier to defer a reckoning?",
            ]),
            ("Where You Feel Most Out Of Integrity", [
                "Where in your financial or professional life do you currently feel the clearest gap between your stated values and your actual behavior or commitments?",
                "Is there a role — in business, family, or philanthropy — that you continue to hold primarily because of inertia, expectation, or fear of what stepping back would mean?",
                "If someone who knew your values well were to examine your financial life in full, where would they find the most significant gap?",
                "If you addressed this gap, what would become possible in your life that is not currently available to you?",
            ]),
            ("The Direction You Life Is Pointing", [
                "Looking at the last three to five years, what recurring choices or commitments show up — the things you keep prioritizing even when you don’t have to?",
                "Where does your energy go most naturally — not where you feel obligated, but where you find yourself drawn to?",
                "Is your life’s direction moving in alignment with what you say matters most to you? Where do you see congruence, and where do you notice an integrity gap?",
                "If this direction continues unchanged for the next decade, what will your life look like — and how do you feel about that?",
                "If someone who didn’t know you read the last five years of your calendar and bank statements, what would they say you care most about?",
                "When you slow down and listen to your intuition, what does it say about your current path?",
                "What would you have to give up — in identity, in obligation, in comfort — to redirect your life toward something more aligned with your intuition?",
            ]),
        ],
    ),
    (
        "evolution", "Evolution", "Purpose", 4,
        [
            ("How Your Relationship With Money Has Evolved", [
                "If you divided your financial life into two or three chapters, what would you call them — and what changed between them?",
                "What experience most shifted how you think and feel about money — not what changed your net worth, but what changed your relationship to it?",
                "Is there a belief about money you held ten years ago that you no longer hold — and what replaced it?",
                "Where in your financial life do you feel the most grown-up — and where does an older script still seem to be running?",
            ]),
            ("The Story Your Family Told About Money", [
                "What was your family's dominant message about money — spoken or unspoken? What did money mean in the household you grew up in?",
                "Was money a source of security, anxiety, status, conflict, or silence in your family — or some combination? Could you elaborate on a few core memories that have cemented these sentiments?",
                "What financial behaviors did you observe in the adults around you, and which of those have you replicated — consciously or not?",
                "Which part of the story you grew up with do you most want to carry forward — and which part are you most ready to revise?",
                "Is there a story your family told about people with more money, or less, that still shapes how you see yourself in relation to your own wealth?",
                "What would it mean to consciously author a different relationship to money than the one you inherited — and what would have to change for that to be real?",
            ]),
            ("Financial Decisions in Retrospect", [
                "What financial decision, when you think about it honestly, do you wish you’d made differently? Not the biggest loss — the one that still carries an emotional charge.",
                "What was at stake in that decision beyond the financial outcome? What relationship, value, or version of yourself was affected?",
                "What did you know at the time and in retrospect, what did you learn?",
                "Has that regret changed how you make financial decisions now — or is the same pattern still present, perhaps in a different form?",
                "Is there a part of you that hasn’t forgiven yourself for this decision? What would it mean to you to release that?",
                "If this regret is pointing toward a value you haven’t yet honored, what would honoring it require of you now? What value is that?",
            ]),
            ("Where Money Overextends Itself", [
                "Are there relationships in your life where money functions as a way of maintaining a distance or closeness — where it bridges a gap that conversation hasn't done?",
                "Have you ever used a financial decision to avoid a harder conversation — a gift instead of an presence or an apology?",
                "Is there an area of your life where financial certainty or control has become a substitute for something else — security, respect, connection, proof of worth?",
                "When you think about the relationships where money shows up as a way of managing the dynamic — what are you trying to protect?",
                "If that pattern no longer served you, what would you have to be willing to feel instead? How would that change your relationships?",
            ]),
        ],
    ),
]

# Items the transcription flagged for the advisor's attention. Nothing was changed; these
# appear as "review" notes in /admin/methodology so Mimi can decide.
KNOWN_ISSUES = {
    "play_s4_q4": "Identical to question 2 in this section.",
    "love_s4_q2": "Possible typo: 'the last time your pursued them' (your -> you).",
    "evolution_s4_q2": "Possible typo: 'a gift instead of an presence' (an -> a).",
    "community_s4_q3": "Possible grammar: 'where do you think it comes from' (it -> they).",
    "work_s2_q2": "Possible wording: 'require a compartmentalization'.",
    "evolution_s3_q3": "Possible punctuation: 'What did you know at the time and in retrospect, what did you learn?'",
    "love_s1_q5": "En dash (-) where the document otherwise uses em dashes; refers to 'your list', which assumes an earlier list-making step.",
    "love_s2_q4": "Refers to 'your list', which assumes an earlier list-making step.",
    "love_s1_q1": "Overlaps with Love > If Money Were Irrelevant #2 and Play > What Comes Intuitively #2 (time disappearing / forgetting the time).",
    "love_s1_q2": "Overlaps with Love > If Money Were Irrelevant #3 (something once loved, now crowded out / stopped).",
    "alignment_s2_q1": "Overlaps with Alignment > What A Fully Aligned Life Looks Like #3 and Out Of Integrity #3 (the clearest / most significant gap).",
}
SECTION_ISSUES = {
    "The Direction You Life Is Pointing": "Possible typo in heading: 'You Life' (You -> Your).",
    "Constrained Generosity – What You Would Donate More Of": "Heading uses an en dash where the document otherwise uses em dashes.",
}

# Approved beta classification. Keys not listed are `optional`. Applied once, to a database
# that has never been classified or answered; afterwards /admin/methodology is the source of truth.
BETA_CORE = [
    "purpose_s1_q1", "purpose_s1_q2",
    "love_s1_q3", "love_s3_q1", "love_s4_q1",
    "play_s3_q1", "play_s3_q4",
    "work_s3_q2", "work_s3_q3",
    "service_s1_q1", "service_s3_q2", "service_s3_q3",
    "community_s1_q1", "community_s4_q1",
    "alignment_s1_q1", "alignment_s3_q5",
    "evolution_s1_q2", "evolution_s2_q1", "evolution_s2_q4", "evolution_s4_q3",
]
BETA_FOLLOW_UP = [
    "love_s1_q1", "love_s1_q2", "love_s1_q4", "love_s3_q2", "love_s3_q3", "love_s4_q2", "love_s4_q3",
    "play_s3_q2",
    "work_s3_q1",
    "service_s1_q2", "service_s3_q1",
    "community_s1_q2", "community_s1_q5", "community_s4_q2",
    "alignment_s1_q3", "alignment_s1_q4", "alignment_s3_q4", "alignment_s3_q6", "alignment_s3_q7",
    "evolution_s1_q3", "evolution_s2_q2", "evolution_s2_q3", "evolution_s2_q6", "evolution_s4_q1",
]
BETA_INACTIVE = ["play_s4_q4"]  # exact duplicate of play_s4_q2; kept and flagged for the advisor


def beta_classification(key: str) -> str:
    if key in BETA_CORE:
        return "core"
    if key in BETA_FOLLOW_UP:
        return "follow_up"
    if key in BETA_INACTIVE:
        return "inactive"
    return "optional"

# Question keys of the pre-import draft set. A database that still holds only these
# (and has no client answers) is upgraded to the source methodology on startup.
DRAFT_V1_KEYS = frozenset({
    "purpose_of_wealth", "meaningful_life", "love_people", "love_money_story", "love_carry_forward", "play_joy", "play_time",
    "work_role", "work_without_money", "work_lessons", "service_meaning", "service_causes", "service_giving_today",
    "alignment_now", "alignment_tension", "alignment_enough", "community_belong", "community_build",
    "evolution_money_change", "evolution_legacy", "evolution_ten_years",
})
