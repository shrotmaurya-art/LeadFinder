# TODO: T10.1 preflight_check not yet implemented.
# When scripts/preflight_check.py is built, uncomment and enable the block below:
#
#   from scripts.preflight_check import run as preflight_run
#   import streamlit as st
#   ok, msg = preflight_run()
#   if not ok:
#       st.error(f"Environment check failed: {msg}")
#       st.stop()

import pandas as pd
import streamlit as st

import config
from analyzer.recommendations import recommend_services
from crm.database import Database
from crm.leads import OptedOutError, STATUS_FLOW, transition_status
from outreach import email_generator, sender, whatsapp_generator
from utils.timeutil import today_local


def _get_selected_rows(sel) -> list[int]:
    if isinstance(sel, dict):
        return sel.get("selection", {}).get("rows", [])
    if hasattr(sel, "selection"):
        s = sel.selection
        if isinstance(s, dict):
            return s.get("rows", [])
        if hasattr(s, "rows"):
            return s.rows
    return []


def main():
    st.set_page_config(page_title="LeadFinder Dashboard", layout="wide")

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
        cats_list = list(cats) if cats else None
        return db.get_dashboard_counts(for_date, city=city, categories=cats_list)

    for_date = today_local()
    counts = _fetch_counts(for_date, tuple(city_filter) if city_filter else None, tuple(cat_filter) if cat_filter else None)

    # ── Metric cards ─────────────────────────────────────────────────

    st.title("LeadFinder Dashboard")

    card_defs = [
        ("Businesses Found Today", counts["businesses_found_today"]),
        ("New Leads", counts["new_leads"]),
        ("Messages Ready", counts["messages_ready"]),
        ("Sent Today", counts["sent_today"]),
        ("Replies", counts["replies"]),
        ("Meetings", counts["meetings"]),
        ("Clients", counts["clients"]),
    ]

    cols = st.columns(7)
    for col, (label, value) in zip(cols, card_defs):
        with col:
            st.metric(label=label, value=value)

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
            table_rows = []
            for lead in review_leads:
                audit = db.get_latest_audit(lead["id"])
                recs = recommend_services(audit) if audit else []
                top_rec = recs[0] if recs else ""
                table_rows.append({
                    "name": lead.get("name", ""),
                    "category": lead.get("category", ""),
                    "lead_score": lead.get("lead_score", 0),
                    "top recommendation": top_rec,
                })

            df = pd.DataFrame(table_rows)
            df_selection = st.dataframe(
                df,
                selection_mode="single-row",
                on_select="rerun",
                hide_index=True,
                use_container_width=True,
                key="leads_dataframe",
            )

            selected_rows = _get_selected_rows(df_selection)

            if selected_rows:
                selected_idx = selected_rows[0]
                if 0 <= selected_idx < len(review_leads):
                    business = review_leads[selected_idx]
                    biz_id = business["id"]
                    audit = db.get_latest_audit(biz_id)
                    recs = recommend_services(audit) if audit else []

                    st.divider()
                    st.subheader(f"Review & Outreach: {business.get('name', '')}")

                    # Audit Flags
                    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
                    with col_a1:
                        st.metric("Has Website", "Yes" if (audit and audit.get("has_website")) else "No")
                    with col_a2:
                        st.metric("Has Business Email", "Yes" if (audit and audit.get("has_business_email")) else "No")
                    with col_a3:
                        st.metric("Has Instagram", "Yes" if (audit and audit.get("has_instagram")) else "No")
                    with col_a4:
                        st.metric("Reviews Count", audit.get("review_count", 0) if audit else 0)

                    st.markdown("**Recommended Services:** " + (", ".join(recs) if recs else "None"))

                    # Draft Generation / Session Caching
                    email_subj_key = f"email_subj_{biz_id}"
                    email_body_key = f"email_body_{biz_id}"
                    wa_body_key = f"wa_body_{biz_id}"
                    follow_up_count = business.get("follow_up_count", 0)

                    if email_subj_key not in st.session_state or email_body_key not in st.session_state:
                        email_draft = email_generator.generate_email(
                            business, audit or {}, recs, follow_up_number=follow_up_count
                        )
                        st.session_state[email_subj_key] = email_draft.get("subject", "")
                        st.session_state[email_body_key] = email_draft.get("body", "")

                    if wa_body_key not in st.session_state:
                        wa_draft = whatsapp_generator.generate_whatsapp(
                            business, audit or {}, recs, follow_up_number=follow_up_count
                        )
                        st.session_state[wa_body_key] = wa_draft

                    # Outreach Drafting & Sending UI
                    col_email, col_wa = st.columns(2)

                    with col_email:
                        st.markdown("### Email Outreach")
                        edited_subject = st.text_input("Subject", key=email_subj_key)
                        edited_email_body = st.text_area("Body", key=email_body_key, height=220)

                        biz_email = business.get("email")
                        manual_email_key = f"manual_email_{biz_id}"
                        save_email_key = f"save_email_{biz_id}"

                        if not biz_email:
                            manual_email = st.text_input(
                                "No business email on file — add one manually to enable Send Email",
                                key=manual_email_key,
                            )
                            save_to_lead = st.checkbox("Save this email to this lead", key=save_email_key)
                        else:
                            manual_email = ""
                            save_to_lead = False

                        btn_col1, btn_col2 = st.columns([1, 1])
                        with btn_col1:
                            if st.button("Send Email", key=f"send_email_{biz_id}"):
                                effective_email = biz_email or manual_email
                                if not effective_email:
                                    st.warning("No email available — try WhatsApp instead")
                                else:
                                    send_business = business if biz_email else {**business, "email": manual_email}
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

                        with btn_col2:
                            email_shown = st.session_state.get(f"email_shown_{biz_id}", False)
                            if st.button("Mark as Sent", key=f"mark_email_sent_{biz_id}", disabled=not email_shown):
                                sender.confirm_sent(biz_id, "email", edited_email_body, follow_up_count)
                                st.success("Email marked as sent!")
                                st.cache_data.clear()
                                st.rerun()

                    with col_wa:
                        st.markdown("### WhatsApp Outreach")
                        edited_wa_body = st.text_area("Message", key=wa_body_key, height=275)

                        btn_col1, btn_col2 = st.columns([1, 1])
                        with btn_col1:
                            if st.button("Send WhatsApp", key=f"send_wa_{biz_id}"):
                                try:
                                    res = sender.prepare_send(business, "whatsapp", None, edited_wa_body)
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
                                    dest_phone = business.get("normalized_phone") or business.get("phone") or "N/A"
                                    st.write(f"**Recipient Phone:** `{dest_phone}`")
                                    st.code(edited_wa_body)
                                    st.info("Copy the phone number and message body above to send manually via WhatsApp.")

                        with btn_col2:
                            wa_shown = st.session_state.get(f"wa_shown_{biz_id}", False)
                            if st.button("Mark as Sent", key=f"mark_wa_sent_{biz_id}", disabled=not wa_shown):
                                sender.confirm_sent(biz_id, "whatsapp", edited_wa_body, follow_up_count)
                                st.success("WhatsApp marked as sent!")
                                st.cache_data.clear()
                                st.rerun()

    # ── Pipeline tab ────────────────────────────────────────────────

    with tab_pipeline:
        st.subheader("Pipeline")

        status_list = list(STATUS_FLOW.keys())
        pipeline_cols = st.columns(len(status_list))

        pipeline_rerun = False

        for col, status_label in zip(pipeline_cols, status_list):
            with col:
                st.markdown(f"**{status_label}**")
                leads = db.get_leads(status=status_label, order_by_score=True)

                if not leads:
                    st.caption("No leads")
                    continue

                for lead in leads:
                    biz_id = lead["id"]
                    current_status = lead["status"]
                    valid_next = sorted(STATUS_FLOW.get(current_status, set()))

                    with st.container(border=True):
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

        if pipeline_rerun:
            st.cache_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()


