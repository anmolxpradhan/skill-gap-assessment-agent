"""
AI-Powered Skill Assessment & Personalised Learning Plan Agent
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
LLM   : Google Gemini 1.5 Flash (free tier — 15 RPM, 1 500 req/day, 1M tokens/day)
UI    : Streamlit (open-source, free)
Parse : PyPDF2 (open-source, free)

Run:
    pip install -r requirements.txt
    streamlit run app.py
"""

import os
import time
from enum import Enum, auto

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv

from core.assessor import (
    SkillSession,
    Turn,
    generate_followup_question,
    generate_opening_question,
    get_transition_message,
    rate_skill,
)
from core.plan_generator import generate_learning_plan
from core.skill_extractor import ExtractionResult, extract_skills
from utils.pdf_parser import parse_resume

load_dotenv()

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Skill Assessment Agent",
    page_icon="✦",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Hide Streamlit chrome */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 2rem; padding-bottom: 6rem; max-width: 780px; }

/* Avatar label inside chat messages */
[data-testid="stChatMessageContent"] p { margin: 0; }

/* Skill pill badges */
.pill {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 600;
    margin: 2px 3px 2px 0;
}
.pill-done    { background: #22c55e22; color: #16a34a; border: 1px solid #22c55e55; }
.pill-active  { background: #6366f122; color: #4f46e5; border: 1px solid #6366f155; }
.pill-pending { background: #94a3b822; color: #64748b; border: 1px solid #94a3b844; }

/* Progress bar */
.pbar-wrap { background: #e2e8f0; border-radius: 99px; height: 6px; width: 100%; margin: 4px 0 8px; }
.pbar-fill  { height: 6px; border-radius: 99px; background: #6366f1; transition: width .4s; }

/* Skill score bars */
.score-label { font-size: 0.78rem; color: #64748b; margin-bottom: 2px; }
.sbar-wrap { background: #f1f5f9; border-radius: 99px; height: 10px; width: 100%; }
.sbar-fill  { height: 10px; border-radius: 99px; transition: width .4s; }

/* Resource links */
.res-row { display: flex; align-items: baseline; gap: 8px; margin: 5px 0; font-size: 0.88rem; }
.res-platform { font-size: 0.72rem; color: #94a3b8; }

/* Readiness chip */
.chip {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 9999px;
    font-size: 0.8rem;
    font-weight: 700;
}

/* Divider replacement */
.soft-divider { border: none; border-top: 1px solid #e2e8f0; margin: 16px 0; }

/* Input area styling */
.stTextArea textarea {
    border-radius: 12px !important;
    font-size: 0.93rem !important;
}
.stFileUploader {
    border-radius: 12px !important;
}
</style>
""", unsafe_allow_html=True)


# ── Stage enum ─────────────────────────────────────────────────────────────────
class Stage(Enum):
    AWAIT_JD      = auto()   # waiting for job description
    AWAIT_RESUME  = auto()   # waiting for resume
    EXTRACTING    = auto()   # analysing JD + resume
    ASSESSMENT    = auto()   # conversational Q&A
    RATING        = auto()   # background rating + transition
    REPORT        = auto()   # final report


# ── Session-state init ─────────────────────────────────────────────────────────
def _init():
    defaults = {
        "stage":       Stage.AWAIT_JD,
        "api_key":     os.getenv("GEMINI_API_KEY", ""),
        "model":       None,
        "messages":    [],        # {"role": "assistant"|"user", "content": str}
        "jd_text":     "",
        "resume_text": "",
        "extraction":  None,
        "sessions":    [],
        "current_idx": 0,
        "input_key":   0,
        "plan":        None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

_init()

GREETING = (
    "Hi! I'm your **Skill Assessment Agent**.\n\n"
    "I go beyond a resume — I'll have a short conversation with you to assess "
    "real proficiency on each skill a role requires, identify gaps, and build a "
    "personalised learning plan with free resources.\n\n"
    "**To begin, paste the job description below.**"
)

# Seed the greeting on first load
if not st.session_state["messages"]:
    st.session_state["messages"].append({"role": "assistant", "content": GREETING})


# ── Helpers ────────────────────────────────────────────────────────────────────
def add_msg(role: str, content: str):
    st.session_state["messages"].append({"role": role, "content": content})


def get_model() -> genai.GenerativeModel:
    genai.configure(api_key=st.session_state["api_key"])
    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=genai.types.GenerationConfig(temperature=0.7, max_output_tokens=1024),
    )


LEVEL_COLORS = {1: "#ef4444", 2: "#f97316", 3: "#eab308", 4: "#3b82f6", 5: "#22c55e"}


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Skill Assessment Agent")
    st.caption("Powered by Gemini 1.5 Flash · free tier")
    st.divider()

    key_val = st.text_input(
        "Gemini API Key",
        value=st.session_state["api_key"],
        type="password",
        help="Free key at aistudio.google.com",
    )
    if key_val:
        st.session_state["api_key"] = key_val

    if st.session_state["api_key"]:
        st.success("API key ready", icon="✅")
    else:
        st.warning("Add your Gemini API key above")

    # Live skill tracker
    if st.session_state["sessions"]:
        st.divider()
        st.caption("Skills")
        idx = st.session_state["current_idx"]
        for i, sess in enumerate(st.session_state["sessions"]):
            if sess.complete:
                cls, icon = "pill-done", "✓"
                suffix = f" {sess.final_rating_label}"
            elif i == idx:
                cls, icon = "pill-active", "›"
                suffix = ""
            else:
                cls, icon = "pill-pending", "○"
                suffix = ""
            st.markdown(
                f'<span class="pill {cls}">{icon} {sess.skill.name}{suffix}</span>',
                unsafe_allow_html=True,
            )

    st.divider()
    if st.button("↺ Start over", use_container_width=True):
        saved_key = st.session_state.get("api_key", "")
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        _init()
        st.session_state["api_key"] = saved_key
        st.session_state["messages"].append({"role": "assistant", "content": GREETING})
        st.rerun()

    st.caption("15 RPM · 1 500 req/day · 1M tokens/day (free)")


# ── Render full message history ────────────────────────────────────────────────
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ════════════════════════════════════════════════════════════════════════════════
#  INPUT LAYER  — rendered below the message history, changes per stage
# ════════════════════════════════════════════════════════════════════════════════

stage = st.session_state["stage"]

# ── AWAIT_JD ──────────────────────────────────────────────────────────────────
if stage == Stage.AWAIT_JD:
    if not st.session_state["api_key"]:
        st.info("Open the sidebar (top-left) and add your Gemini API key to get started.")

    with st.form("jd_form", clear_on_submit=True):
        jd_input = st.text_area(
            "Job description",
            placeholder="Paste the full job description here…",
            height=220,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button(
            "Submit JD →",
            use_container_width=True,
            disabled=not st.session_state["api_key"],
        )

    if submitted and jd_input.strip():
        jd = jd_input.strip()
        st.session_state["jd_text"] = jd

        # Show truncated JD as user message
        preview = jd[:300] + ("…" if len(jd) > 300 else "")
        add_msg("user", f"**Job Description:**\n\n{preview}")

        add_msg("assistant", (
            "Got it — I've read through the job description.\n\n"
            "Now please **upload the candidate's resume** (PDF or TXT). "
            "You can also paste the text directly if you prefer."
        ))
        st.session_state["stage"] = Stage.AWAIT_RESUME
        st.rerun()


# ── AWAIT_RESUME ──────────────────────────────────────────────────────────────
elif stage == Stage.AWAIT_RESUME:
    resume_file = st.file_uploader(
        "Upload resume (PDF or TXT)",
        type=["pdf", "txt"],
        label_visibility="collapsed",
        key=f"resume_upload_{st.session_state['input_key']}",
    )
    with st.form("resume_form", clear_on_submit=True):
        resume_paste = st.text_area(
            "Or paste resume text",
            placeholder="Paste resume text here if you don't have a file…",
            height=160,
            label_visibility="collapsed",
        )
        col1, col2 = st.columns([3, 1])
        with col2:
            go = st.form_submit_button("Continue →", use_container_width=True)

    if go and (resume_file or resume_paste.strip()):
        if resume_file:
            resume_text = parse_resume(resume_file.read(), resume_file.name)
            src = f"📄 `{resume_file.name}` uploaded"
        else:
            resume_text = resume_paste.strip()
            src = "Resume text received"

        st.session_state["resume_text"] = resume_text
        add_msg("user", src)
        add_msg("assistant", "Perfect — let me analyse the job description and resume together…")
        st.session_state["stage"] = Stage.EXTRACTING
        st.rerun()


# ── EXTRACTING ────────────────────────────────────────────────────────────────
elif stage == Stage.EXTRACTING:
    with st.spinner("Extracting skills and building assessment plan…"):
        model = get_model()
        st.session_state["model"] = model

        try:
            extraction: ExtractionResult = extract_skills(
                st.session_state["jd_text"],
                st.session_state["resume_text"],
                model,
            )
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            st.stop()

        st.session_state["extraction"] = extraction
        c = extraction.candidate

        # Build sessions
        claimed_set = {s.lower() for s in c.claimed_skills}
        sessions = [
            SkillSession(
                skill=sk,
                candidate_claimed=(
                    sk.name.lower() in claimed_set
                    or any(sk.name.lower() in x.lower() for x in c.claimed_skills)
                ),
            )
            for sk in extraction.required_skills
        ]
        st.session_state["sessions"] = sessions
        st.session_state["current_idx"] = 0

        # Extraction summary message
        skill_pills = " ".join(
            f'<span class="pill pill-pending">○ {sk.skill.name}</span>'
            for sk in sessions
        )
        name_line = f"**{c.name}**" if c.name else "**Candidate**"
        role_line = f" · {c.current_role}" if c.current_role else ""
        yoe_line  = f" · {c.years_experience} yrs exp" if c.years_experience else ""
        edu_line  = f"\n🎓 {c.education}" if c.education else ""

        summary_md = (
            f"Here's what I found:\n\n"
            f"👤 {name_line}{role_line}{yoe_line}{edu_line}\n\n"
            f"**{len(sessions)} skills to assess:**\n\n"
            f"{skill_pills}\n\n"
            f"I'll ask you **3 questions per skill** — "
            f"conceptual, practical, then a scenario. Ready? Let's go.\n\n---"
        )
        add_msg("assistant", summary_md)

        # Generate opening question for skill 0
        first = sessions[0]
        opening_q = generate_opening_question(first.skill, c, first.candidate_claimed, model)
        first.turns.append(Turn(role="assessor", text=opening_q))
        first.question_count = 1
        add_msg("assistant", opening_q)

        st.session_state["stage"] = Stage.ASSESSMENT
        st.rerun()


# ── ASSESSMENT ────────────────────────────────────────────────────────────────
elif stage == Stage.ASSESSMENT:
    sessions    = st.session_state["sessions"]
    current_idx = st.session_state["current_idx"]
    model       = st.session_state["model"]
    extraction  = st.session_state["extraction"]
    current     = sessions[current_idx]

    # Progress indicator
    total      = len(sessions)
    done_count = sum(1 for s in sessions if s.complete)
    pct        = int(done_count / total * 100)
    q_of       = current.question_count
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;font-size:0.78rem;color:#94a3b8;">'
        f'<span>Skill {done_count + 1} of {total} &nbsp;·&nbsp; Question {q_of} of 3</span>'
        f'<span>{pct}%</span></div>'
        f'<div class="pbar-wrap"><div class="pbar-fill" style="width:{pct}%;"></div></div>',
        unsafe_allow_html=True,
    )

    # Answer input via chat_input (fixed at bottom, feels natural)
    answer = st.chat_input("Your answer…", key=f"chat_in_{st.session_state['input_key']}")

    if answer and answer.strip():
        ans = answer.strip()
        add_msg("user", ans)
        current.turns.append(Turn(role="candidate", text=ans))

        if current.question_count >= 3:
            st.session_state["stage"] = Stage.RATING
            st.session_state["input_key"] += 1
        else:
            with st.spinner(""):
                followup = generate_followup_question(current, model, extraction.candidate)
                time.sleep(0.3)
            current.turns.append(Turn(role="assessor", text=followup))
            current.question_count += 1
            add_msg("assistant", followup)
            st.session_state["input_key"] += 1

        st.rerun()


# ── RATING ────────────────────────────────────────────────────────────────────
elif stage == Stage.RATING:
    sessions    = st.session_state["sessions"]
    current_idx = st.session_state["current_idx"]
    model       = st.session_state["model"]
    extraction  = st.session_state["extraction"]
    current     = sessions[current_idx]

    with st.spinner(f"Evaluating {current.skill.name}…"):
        rate_skill(current, model)
        time.sleep(0.3)

    next_idx = current_idx + 1
    has_next = next_idx < len(sessions)
    next_skill = sessions[next_idx].skill if has_next else None

    with st.spinner(""):
        transition = get_transition_message(current, next_skill, model)
        time.sleep(0.3)

    if has_next:
        nxt = sessions[next_idx]
        with st.spinner(""):
            opening_q = generate_opening_question(
                nxt.skill, extraction.candidate, nxt.candidate_claimed, model
            )
            time.sleep(0.3)
        nxt.turns.append(Turn(role="assessor", text=opening_q))
        nxt.question_count = 1
        add_msg("assistant", transition)
        add_msg("assistant", opening_q)
        st.session_state["current_idx"] = next_idx
        st.session_state["input_key"] += 1
        st.session_state["stage"] = Stage.ASSESSMENT
    else:
        add_msg("assistant", transition)
        st.session_state["stage"] = Stage.REPORT

    st.rerun()


# ── REPORT ────────────────────────────────────────────────────────────────────
elif stage == Stage.REPORT:
    sessions   = st.session_state["sessions"]
    model      = st.session_state["model"]
    extraction = st.session_state["extraction"]

    if st.session_state["plan"] is None:
        with st.spinner("Building your personalised learning plan…"):
            try:
                plan = generate_learning_plan(
                    sessions, extraction.candidate, extraction.job_title, model
                )
                st.session_state["plan"] = plan
            except Exception as e:
                st.error(f"Could not generate learning plan: {e}")
                st.stop()

        # Drop a closing chat message
        readiness_icons = {
            "Strong Match": "You're in great shape for this role.",
            "Good Candidate": "You're a solid candidate with a few areas to strengthen.",
            "Needs Preparation": "There are some meaningful gaps — let's build a plan.",
            "Significant Gap": "There's meaningful ground to cover — here's your roadmap.",
        }
        plan = st.session_state["plan"]
        closing = (
            f"**Assessment complete.** {readiness_icons.get(plan.readiness_label, '')}\n\n"
            f"Overall readiness: **{plan.overall_readiness_pct}%** · {plan.readiness_label} · "
            f"~{plan.total_estimated_weeks} weeks to close gaps\n\n"
            f"{plan.executive_summary}\n\n"
            f"*Full report below.*"
        )
        add_msg("assistant", closing)
        st.rerun()

    plan = st.session_state["plan"]

    # ── Report UI ──────────────────────────────────────────────────────────────
    st.markdown("<hr class='soft-divider'>", unsafe_allow_html=True)

    READINESS_COLORS = {
        "Strong Match": "#22c55e",
        "Good Candidate": "#3b82f6",
        "Needs Preparation": "#f59e0b",
        "Significant Gap": "#ef4444",
    }
    chip_color = READINESS_COLORS.get(plan.readiness_label, "#6366f1")

    col1, col2, col3 = st.columns(3)
    col1.metric("Readiness", f"{plan.overall_readiness_pct}%")
    col2.markdown(
        f'<br><span class="chip" style="background:{chip_color}22;color:{chip_color};'
        f'border:1px solid {chip_color}55;">{plan.readiness_label}</span>',
        unsafe_allow_html=True,
    )
    col3.metric("Est. prep time", f"~{plan.total_estimated_weeks} weeks")

    st.markdown("<hr class='soft-divider'>", unsafe_allow_html=True)

    tab_scores, tab_plan = st.tabs(["Skill Scores", "Learning Plan"])

    # ── TAB: Skill Scores ──────────────────────────────────────────────────────
    with tab_scores:
        if plan.strengths:
            st.caption("Strengths — meets or exceeds requirement")
            st.markdown(
                " ".join(f'<span class="pill pill-done">✓ {s}</span>' for s in plan.strengths),
                unsafe_allow_html=True,
            )
            st.markdown("<br>", unsafe_allow_html=True)

        st.caption("All assessed skills")
        for sess in sessions:
            if sess.final_rating is None:
                continue
            req    = sess.skill.required_level
            actual = sess.final_rating
            gap    = req - actual
            actual_color = LEVEL_COLORS.get(actual, "#6366f1")
            req_color    = LEVEL_COLORS.get(req, "#6366f1")

            icon = "✓" if gap <= 0 else ("!" if gap == 1 else "!!")
            imp  = sess.skill.importance
            imp_color = "#ef444422" if imp == "must-have" else "#6366f122"
            imp_text  = "#ef4444"   if imp == "must-have" else "#6366f1"

            with st.expander(
                f"{icon}  {sess.skill.name}   {sess.final_rating_label} → required {sess.skill.required_level_label}",
                expanded=(gap > 1 and imp == "must-have"),
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown('<div class="score-label">Your level</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="sbar-wrap"><div class="sbar-fill" '
                        f'style="width:{actual*20}%;background:{actual_color};"></div></div>'
                        f'<span style="font-size:.8rem;color:{actual_color};">'
                        f'{sess.final_rating_label} ({actual}/5)</span>',
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown('<div class="score-label">Required</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="sbar-wrap"><div class="sbar-fill" '
                        f'style="width:{req*20}%;background:{req_color};"></div></div>'
                        f'<span style="font-size:.8rem;color:{req_color};">'
                        f'{sess.skill.required_level_label} ({req}/5)</span>',
                        unsafe_allow_html=True,
                    )
                if sess.rating_rationale:
                    st.markdown(f"\n{sess.rating_rationale}")
                st.markdown(
                    f'<span class="pill" style="background:{imp_color};color:{imp_text};'
                    f'border:1px solid {imp_text}44;">{imp}</span>',
                    unsafe_allow_html=True,
                )

    # ── TAB: Learning Plan ─────────────────────────────────────────────────────
    with tab_plan:
        if not plan.items:
            st.success("No significant gaps — you appear ready for this role!")
        else:
            st.caption(
                f"Prioritised by impact · ~{plan.total_estimated_weeks} weeks total "
                f"(with parallel learning)"
            )

            PRIO_COLORS = {"critical": "#ef4444", "important": "#f59e0b", "optional": "#6366f1"}
            TYPE_ICONS  = {"video": "▶", "course": "◉", "documentation": "◈", "tutorial": "◇", "book": "◆"}

            for i, item in enumerate(
                sorted(plan.items, key=lambda x: {"critical": 0, "important": 1, "optional": 2}.get(x.priority, 1)),
                1,
            ):
                pc = PRIO_COLORS.get(item.priority, "#6366f1")
                with st.expander(
                    f"{i}.  {item.skill_name}   {item.current_label} → {item.required_label}   "
                    f"~{item.estimated_weeks}w",
                    expanded=(i == 1),
                ):
                    # Meta row
                    st.markdown(
                        f'<span class="pill" style="background:{pc}22;color:{pc};border:1px solid {pc}44;">'
                        f'{item.priority.upper()}</span>'
                        f'<span class="pill pill-pending">{item.estimated_weeks} weeks · '
                        f'{item.weekly_hours}h/week</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"*{item.rationale}*")

                    if item.adjacent_skills_leveraged:
                        st.markdown(
                            "**Builds on:** "
                            + "  ·  ".join(item.adjacent_skills_leveraged)
                        )

                    st.markdown("**What to cover, in order:**")
                    for j, step in enumerate(item.learning_path, 1):
                        st.markdown(f"&ensp;{j}. {step}")

                    st.markdown("**Free resources:**")
                    for res in item.resources:
                        icon = TYPE_ICONS.get(res.type, "◌")
                        st.markdown(
                            f'<div class="res-row">{icon} '
                            f'<a href="{res.url}" target="_blank">{res.title}</a>'
                            f'<span class="res-platform">{res.platform}</span></div>',
                            unsafe_allow_html=True,
                        )
