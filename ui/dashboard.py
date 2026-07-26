# TODO: T10.1 preflight_check not yet implemented.
# When scripts/preflight_check.py is built, uncomment and enable the block below:
#
#   from scripts.preflight_check import run as preflight_run
#   import streamlit as st
#   ok, msg = preflight_run()
#   if not ok:
#       st.error(f"Environment check failed: {msg}")
#       st.stop()

from datetime import date, timedelta

import streamlit as st

import config
from analyzer.recommendations import recommend_services
from crm.database import Database
from crm.leads import OptedOutError, STATUS_FLOW, transition_status
from outreach import email_generator, sender, whatsapp_generator
from utils.timeutil import today_local

CUSTOM_CSS = """
<style>
/* ── Card spacing & shadow ─────────────────────────────── */
.lead-card {
    border-left: 5px solid #ccc;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,.12);
    padding: 1rem 1.2rem;
    margin-bottom: .75rem;
    background: #fff;
}
.lead-card.status-new        { border-left-color: #6c757d; }
.lead-card.status-ready      { border-left-color: #28a745; }
.lead-card.status-contacted  { border-left-color: #007bff; }
.lead-card.status-replied    { border-left-color: #17a2b8; }
.lead-card.status-meeting    { border-left-color: #fd7e14; }
.lead-card.status-client     { border-left-color: #20c997; }
.lead-card.status-closed     { border-left-color: #adb5bd; }

/* ── Score badges ───────────────────────────────────────── */
.score-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-weight: 600;
    font-size: .85rem;
    color: #fff;
}
.score-badge-lg {
    display: inline-block;
    padding: 6px 18px;
    border-radius: 14px;
    font-weight: 700;
    font-size: 1.3rem;
    color: #fff;
}
.score-low   { background: #dc3545; }
.score-mid   { background: #fd7e14; }
.score-high  { background: #28a745; }

/* ── Audit flag icons ──────────────────────────────────── */
.audit-yes { color: #28a745; font-weight: 700; }
.audit-no  { color: #dc3545; font-weight: 700; }
.audit-count { color: #007bff; font-weight: 700; }

/* ── Sent confirmation ─────────────────────────────────── */
.sent-confirm {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 6px;
    background: #d4edda;
    color: #155724;
    font-weight: 600;
    font-size: .9rem;
}

/* ── Pipeline column shading ────────────────────────────── */
.pipeline-col-even {
    background: #f8f9fa;
    border-radius: 8px;
    padding: .75rem;
}
.pipeline-col-odd {
    background: #ffffff;
    border-radius: 8px;
    padding: .75rem;
}
.pipeline-count-badge {
    display: inline-block;
    background: #dee2e6;
    border-radius: 10px;
    padding: 1px 8px;
    font-size: .8rem;
    margin-left: 6px;
    vertical-align: middle;
}
</style>
"""


def _score_badge_html(score: int, *, large: bool = False) -> str:
    size_cls = "score-badge-lg" if large else "score-badge"
    if score < 40:
        color_cls = "score-low"
    elif score < 70:
        color_cls = "score-mid"
    else:
        color_cls = "score-high"
    return f'<span class="{size_cls} {color_cls}">{score}</span>'


def _truncate_name(name: str, max_len: int = 40) -> str:
    return name if len(name) <= max_len else name[:max_len - 3] + "..."


def _audit_flag_html(label: str, present: bool) -> str:
    icon = '<span class="audit-yes">\u2713</span>' if present else '<span class="audit-no">\u2715</span>'
    return f"{icon} {label}"


def _pipeline_status_css_class(status: str) -> str:
    mapping = {
        "New": "status-new",
        "Ready to Contact": "status-ready",
        "Contacted": "status-contacted",
        "Replied": "status-replied",
        "Meeting Scheduled": "status-meeting",
        "Client": "status-client",
        "Closed": "status-closed",
    }
    return mapping.get(status, "status-new")



def main():
    st.set_page_config(page_title="LeadFinderAI", page_icon="\U0001F4CD", layout="wide")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    # ── Sidebar filters ──────────────────────────────────────────────

    db = Database()

    @st.cache_data(ttl=30)
    def _fetch_filter_options() -> tuple[list[str], list[str]]:
        return sorted(config.CITIES), sorted(config.CATEGORIES)

    cities, categories = _fetch_filter_options()

    with st.sidebar:
        st.header("Filters")
        city_selection = st.multiselect("City", ["all"] + cities, default=["all"])
        category_selection = st.multiselect("Category", ["all"] + categories, default=["all"])

    # Resolve filter values: "all" → None (no filter)
    city_filter = None if "all" in city_selection else city_selection
    cat_filter = None if "all" in category_selection else category_selection

    # ── Data fetching (cached) ───────────────────────────────────────

    @st.cache_data(ttl=30)
    def _fetch_counts(for_date: str, city: str | list[str] | None, cats: tuple[str, ...] | None) -> dict:
        city_list = list(city) if isinstance(city, tuple) else city
        cats_list = list(cats) if cats else None
        return db.get_dashboard_counts(for_date, city=city_list, categories=cats_list)

    for_date = today_local()
    counts = _fetch_counts(for_date, tuple(city_filter) if city_filter else None, tuple(cat_filter) if cat_filter else None)

    # Yesterday's counts for delta indicators
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    counts_yesterday = _fetch_counts(yesterday, tuple(city_filter) if city_filter else None, tuple(cat_filter) if cat_filter else None)

    # ── Persistent sidebar: today's numbers ──────────────────────────

    with st.sidebar:
        st.divider()
        st.subheader("Today at a Glance")
        st.metric("Found", counts["businesses_found_today"])
        st.metric("New Leads", counts["new_leads"])
        st.metric("Messages Ready", counts["messages_ready"])

    # ── Metric cards with header and deltas ──────────────────────────

    st.title("LeadFinder Dashboard")
    st.subheader("Today's Metrics")

    card_defs = [
        ("Businesses Found Today", counts["businesses_found_today"], counts_yesterday["businesses_found_today"]),
        ("New Leads", counts["new_leads"], counts_yesterday["new_leads"]),
        ("Messages Ready", counts["messages_ready"], counts_yesterday["messages_ready"]),
        ("Sent Today", counts["sent_today"], counts_yesterday["sent_today"]),
        ("Replies", counts["replies"], counts_yesterday["replies"]),
        ("Meetings", counts["meetings"], counts_yesterday["meetings"]),
        ("Clients", counts["clients"], counts_yesterday["clients"]),
    ]

    metric_cols = st.columns(7)
    for col, (label, today_val, yest_val) in zip(metric_cols, card_defs):
        with col:
            delta = today_val - yest_val
            st.metric(label=label, value=today_val, delta=delta, delta_color="normal")

    # ── Tabs ────────────────────────────────────────────────────────

    tab_overview, tab_pipeline = st.tabs(["Overview", "Pipeline"])

    # ── Overview: Leads to Review ───────────────────────────────────

    with tab_overview:
        st.subheader("Leads to Review")

        raw_leads = db.get_leads(status="Ready to Contact", city=city_filter, order_by_score=True)
        if cat_filter:
            review_leads = [l for l in raw_leads if l.get("category") in cat_filter]
        else:
            review_leads = raw_leads

        if not review_leads:
            st.info("No leads ready to contact.")
        else:
            for idx, lead in enumerate(review_leads):
                biz_id = lead["id"]
                audit = db.get_latest_audit(biz_id)
                recs = recommend_services(audit) if audit else []

                name = lead.get("name", "Unknown")
                category = lead.get("category", "N/A")
                city = lead.get("city", "N/A")
                score = lead.get("lead_score", 0)

                display_name = _truncate_name(name)
                label = f"{display_name} \u2014 {category} \u2022 {city}"
                with st.expander(label, expanded=False):
                    # (a) Score badge — large, first thing visible
                    st.markdown(_score_badge_html(score, large=True), unsafe_allow_html=True)

                    # (b) Audit flags with check/cross icons
                    has_website = bool(audit and audit.get("has_website"))
                    has_email = bool(audit and audit.get("has_business_email"))
                    has_ig = bool(audit and audit.get("has_instagram"))
                    review_count = audit.get("review_count", 0) if audit else 0
                    af1, af2, af3, af4 = st.columns(4)
                    with af1:
                        st.markdown(_audit_flag_html("Website", has_website), unsafe_allow_html=True)
                    with af2:
                        st.markdown(_audit_flag_html("Biz Email", has_email), unsafe_allow_html=True)
                    with af3:
                        st.markdown(_audit_flag_html("Instagram", has_ig), unsafe_allow_html=True)
                    with af4:
                        st.markdown(f'<span class="audit-count">{review_count}</span> Reviews', unsafe_allow_html=True)

                    # (c) Recommended services — plain comma list
                    st.markdown("**Recommended Services:** " + (", ".join(recs) if recs else "None"))

                    # Draft loading: DB first, then generate + persist if missing
                    email_subj_key = f"email_subj_{biz_id}"
                    email_body_key = f"email_body_{biz_id}"
                    wa_body_key = f"wa_body_{biz_id}"
                    follow_up_count = lead.get("follow_up_count", 0)

                    saved_draft = db.get_draft(biz_id)

                    if saved_draft is not None:
                        # Restore persisted draft into session state widgets
                        st.session_state[email_subj_key] = saved_draft["draft_email_subject"] or ""
                        st.session_state[email_body_key] = saved_draft["draft_email_body"] or ""
                        st.session_state[wa_body_key] = saved_draft["draft_whatsapp_message"] or ""
                    else:
                        # No persisted draft — generate once and save immediately
                        if email_subj_key not in st.session_state or email_body_key not in st.session_state:
                            email_draft = email_generator.generate_email(
                                lead, audit or {}, recs, follow_up_number=follow_up_count
                            )
                            st.session_state[email_subj_key] = email_draft.get("subject", "")
                            st.session_state[email_body_key] = email_draft.get("body", "")

                        if wa_body_key not in st.session_state:
                            wa_draft = whatsapp_generator.generate_whatsapp(
                                lead, audit or {}, recs, follow_up_number=follow_up_count
                            )
                            st.session_state[wa_body_key] = wa_draft

                        db.save_draft(
                            biz_id,
                            st.session_state.get(email_subj_key, ""),
                            st.session_state.get(email_body_key, ""),
                            st.session_state.get(wa_body_key, ""),
                        )

                    # (d) Email and WhatsApp side-by-side, each fully self-contained
                    col_email, col_wa = st.columns(2)

                    # ── Email channel ─────────────────────────────────
                    with col_email:
                        st.markdown("### Email Outreach")
                        edited_subject = st.text_input("Subject", key=email_subj_key)
                        edited_email_body = st.text_area("Body", key=email_body_key, height=220)

                        # Persist any edits back to DB
                        db.save_draft(biz_id, edited_subject, edited_email_body, None)

                        email_sent_key = f"email_sent_{biz_id}"
                        if st.session_state.get(email_sent_key):
                            st.markdown(
                                '<span class="sent-confirm">\u2713 Sent via Email</span>',
                                unsafe_allow_html=True,
                            )
                        else:
                            # Regenerate button
                            if st.button("\U0001f504 Regenerate Email", key=f"regen_email_{biz_id}"):
                                new_draft = email_generator.generate_email(
                                    lead, audit or {}, recs, follow_up_number=follow_up_count
                                )
                                st.session_state[email_subj_key] = new_draft.get("subject", "")
                                st.session_state[email_body_key] = new_draft.get("body", "")
                                db.save_draft(
                                    biz_id,
                                    new_draft.get("subject", ""),
                                    new_draft.get("body", ""),
                                    None,
                                )
                                st.rerun()

                            biz_email = lead.get("email")
                            manual_email_key = f"manual_email_{biz_id}"
                            save_email_key = f"save_email_{biz_id}"

                            if not biz_email:
                                manual_email = st.text_input(
                                    "No business email on file \u2014 add one manually to enable Send Email",
                                    key=manual_email_key,
                                )
                                save_to_lead = st.checkbox("Save this email to this lead", key=save_email_key)
                            else:
                                manual_email = ""
                                save_to_lead = False

                            if st.button("Send Email", key=f"send_email_{biz_id}"):
                                effective_email = biz_email or manual_email
                                if not effective_email:
                                    st.warning("No email available \u2014 try WhatsApp instead")
                                else:
                                    send_business = lead if biz_email else {**lead, "email": manual_email}
                                    try:
                                        res = sender.prepare_send(send_business, "email", edited_subject, edited_email_body)
                                    except OptedOutError as e:
                                        res = {"blocked": True, "reason": str(e)}
                                    st.session_state[f"email_res_{biz_id}"] = res
                                    if not res.get("blocked"):
                                        st.session_state[f"email_shown_{biz_id}"] = True
                                    if save_to_lead and manual_email:
                                        db.update_email(biz_id, manual_email)

                            email_res = st.session_state.get(f"email_res_{biz_id}")
                            if email_res:
                                if email_res.get("blocked"):
                                    st.warning(email_res.get("reason", "Send blocked"))
                                else:
                                    dest_email = (biz_email or manual_email) or "N/A"
                                    if email_res.get("link"):
                                        st.link_button("Open Email Client", email_res["link"])
                                    if email_res.get("fallback") == "copy":
                                        st.write(f"**Recipient Email:** `{dest_email}`")
                                        st.code(edited_email_body)
                                        st.info("Copy the recipient email and message body above to send manually in your email program.")

                            email_shown = st.session_state.get(f"email_shown_{biz_id}", False)
                            if st.button("Mark as Sent", key=f"mark_email_sent_{biz_id}", disabled=not email_shown):
                                sender.confirm_sent(biz_id, "email", edited_email_body, follow_up_count)
                                db.clear_draft(biz_id, "email")
                                st.session_state[email_sent_key] = True
                                st.cache_data.clear()
                                st.rerun()

                    # ── WhatsApp channel ──────────────────────────────
                    with col_wa:
                        st.markdown("### WhatsApp Outreach")
                        edited_wa_body = st.text_area("Message", key=wa_body_key, height=275)

                        # Persist any edits back to DB
                        db.save_draft(biz_id, None, None, edited_wa_body)

                        wa_sent_key = f"wa_sent_{biz_id}"
                        if st.session_state.get(wa_sent_key):
                            st.markdown(
                                '<span class="sent-confirm">\u2713 Sent via WhatsApp</span>',
                                unsafe_allow_html=True,
                            )
                        else:
                            # Regenerate button
                            if st.button("\U0001f504 Regenerate WhatsApp", key=f"regen_wa_{biz_id}"):
                                new_wa = whatsapp_generator.generate_whatsapp(
                                    lead, audit or {}, recs, follow_up_number=follow_up_count
                                )
                                st.session_state[wa_body_key] = new_wa
                                db.save_draft(biz_id, None, None, new_wa)
                                st.rerun()

                            if st.button("Send WhatsApp", key=f"send_wa_{biz_id}"):
                                try:
                                    res = sender.prepare_send(lead, "whatsapp", None, edited_wa_body)
                                except OptedOutError as e:
                                    res = {"blocked": True, "reason": str(e)}
                                st.session_state[f"wa_res_{biz_id}"] = res
                                if not res.get("blocked"):
                                    st.session_state[f"wa_shown_{biz_id}"] = True

                            wa_res = st.session_state.get(f"wa_res_{biz_id}")
                            if wa_res:
                                if wa_res.get("blocked"):
                                    st.warning(wa_res.get("reason", "Send blocked"))
                                else:
                                    if wa_res.get("link"):
                                        st.link_button("Open WhatsApp", wa_res["link"])
                                    if wa_res.get("fallback") == "copy":
                                        dest_phone = lead.get("normalized_phone") or lead.get("phone") or "N/A"
                                        st.write(f"**Recipient Phone:** `{dest_phone}`")
                                        st.code(edited_wa_body)
                                        st.info("Copy the phone number and message body above to send manually via WhatsApp.")

                            wa_shown = st.session_state.get(f"wa_shown_{biz_id}", False)
                            if st.button("Mark as Sent", key=f"mark_wa_sent_{biz_id}", disabled=not wa_shown):
                                sender.confirm_sent(biz_id, "whatsapp", edited_wa_body, follow_up_count)
                                db.clear_draft(biz_id, "whatsapp")
                                st.session_state[wa_sent_key] = True
                                st.cache_data.clear()
                                st.rerun()

    # ── Pipeline tab ────────────────────────────────────────────────

    with tab_pipeline:
        st.subheader("Pipeline")

        status_list = list(STATUS_FLOW.keys())
        pipeline_cols = st.columns(len(status_list))

        pipeline_rerun = False

        for idx, (col, status_label) in enumerate(zip(pipeline_cols, status_list)):
            with col:
                shading_cls = "pipeline-col-even" if idx % 2 == 0 else "pipeline-col-odd"
                st.markdown(f'<div class="{shading_cls}">', unsafe_allow_html=True)

                leads = db.get_leads(status=status_label, order_by_score=True)
                count = len(leads)
                st.markdown(f"**{status_label}** <span class='pipeline-count-badge'>{count}</span>", unsafe_allow_html=True)

                if not leads:
                    st.caption("No leads")
                else:
                    for lead in leads:
                        biz_id = lead["id"]
                        current_status = lead["status"]
                        valid_next = sorted(STATUS_FLOW.get(current_status, set()))

                        card_cls = _pipeline_status_css_class(current_status)
                        st.markdown(f'<div class="lead-card {card_cls}">', unsafe_allow_html=True)
                        st.markdown(f"**{lead.get('name', 'Unknown')}**")
                        st.caption(f"{lead.get('city') or 'N/A'} \u2022 Score: {lead.get('lead_score', 0)}")

                        if valid_next:
                            options = ["(no change)"] + valid_next
                            widget_key = f"pipeline_{biz_id}_{current_status}"
                            st.selectbox(
                                "Move to",
                                options=options,
                                key=widget_key,
                                label_visibility="collapsed",
                            )
                            chosen = st.session_state.get(widget_key, "(no change)")
                            if chosen != "(no change)":
                                transition_status(biz_id, chosen, db)
                                del st.session_state[widget_key]
                                pipeline_rerun = True
                        else:
                            st.caption("Terminal status")

                        st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("</div>", unsafe_allow_html=True)

        if pipeline_rerun:
            st.cache_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()
