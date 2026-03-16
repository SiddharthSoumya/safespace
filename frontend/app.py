from __future__ import annotations

import pandas as pd
import requests
import streamlit as st

try:
    from frontend.client import (
        APIError,
        BACKEND_BASE_URL,
        add_follow_up,
        admin_analytics,
        admin_get_complaint,
        admin_list_complaints,
        admin_reply,
        admin_update_status,
        health_check,
        lookup_complaint,
        submit_complaint,
    )
except ModuleNotFoundError:
    from client import (
        APIError,
        BACKEND_BASE_URL,
        add_follow_up,
        admin_analytics,
        admin_get_complaint,
        admin_list_complaints,
        admin_reply,
        admin_update_status,
        health_check,
        lookup_complaint,
        submit_complaint,
    )

st.set_page_config(page_title="SafeSpace Pro", page_icon="🛡️", layout="wide")

st.title("🛡️ SafeSpace Pro")
st.caption("Anonymous harassment reporting, secure ticket follow-up, and HR/legal analytics dashboard.")

with st.sidebar:
    st.header("Navigation")
    page = st.radio("Go to", ["Submit Complaint", "Check Ticket", "HR/Admin Dashboard", "About"], label_visibility="collapsed")
    st.divider()
    st.write(f"**Backend:** `{BACKEND_BASE_URL}`")
    if st.button("Check API Health"):
        try:
            info = health_check()
            st.success(f"API OK — {info['app']}")
        except requests.RequestException:
            st.error("Could not reach backend. Start FastAPI first or update BACKEND_BASE_URL.")
        except APIError as exc:
            st.error(str(exc))


def render_messages(messages: list[dict]) -> None:
    for message in messages:
        role = "👤 Reporter" if message["sender_role"] == "complainant" else "🧑‍⚖️ HR/Admin"
        with st.container(border=True):
            st.markdown(f"**{role}** · {message['created_at']}")
            st.write(message["text"])


if page == "Submit Complaint":
    st.subheader("Submit a complaint")
    st.info("Your identity is optional. If you provide it, it is encrypted before storage.")

    with st.form("submit_complaint_form"):
        text = st.text_area(
            "Describe the incident",
            height=220,
            placeholder="Include what happened, when it happened, who was involved, and whether this is ongoing.",
        )
        identity = st.text_input("Optional identity / email / employee ID")
        department = st.selectbox(
            "Department (optional)",
            ["", "Engineering", "HR", "Sales", "Marketing", "Operations", "Finance", "Support", "Other"],
        )
        mode = st.radio("Categorization mode", ["Auto classify", "Manual category"], horizontal=True)
        manual_category = None
        if mode == "Manual category":
            manual_category = st.selectbox(
                "Choose category",
                ["verbal harassment", "physical harassment", "digital harassment", "other"],
            )
        submitted = st.form_submit_button("Submit complaint")

    if submitted:
        try:
            payload = {
                "text": text,
                "identity": identity or None,
                "department": department or None,
                "use_auto_classification": mode == "Auto classify",
                "manual_category": manual_category,
            }
            result = submit_complaint(payload)
            st.success("Complaint submitted successfully.")
            st.warning("Save these credentials now. The access code is only shown once.")
            col1, col2 = st.columns(2)
            col1.metric("Ticket ID", result["ticket_id"])
            col2.metric("Access Code", result["access_code"])
            st.write(f"**Predicted category:** {result['category']}  ")
            st.write(f"**Severity:** {result['severity']}")
        except requests.RequestException:
            st.error("Could not connect to backend. Make sure FastAPI is running.")
        except APIError as exc:
            st.error(str(exc))

elif page == "Check Ticket":
    st.subheader("Check your ticket and send follow-up messages")

    ticket_id = st.text_input("Ticket ID", placeholder="SAFE-20260308-ABC123")
    access_code = st.text_input("Access Code", type="password")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Load ticket", use_container_width=True):
            try:
                detail = lookup_complaint(ticket_id.strip(), access_code.strip())
                st.session_state["ticket_detail"] = detail
            except requests.RequestException:
                st.error("Could not connect to backend.")
            except APIError as exc:
                st.error(str(exc))

    detail = st.session_state.get("ticket_detail")
    if detail and detail.get("ticket_id") == ticket_id.strip():
        left, right = st.columns(2)
        left.metric("Category", detail["category"])
        right.metric("Status", detail["status"])
        st.write(f"**Severity:** {detail['severity']}  ")
        st.write(f"**Department:** {detail.get('department') or 'Unspecified'}")
        st.write("**Original complaint**")
        st.write(detail["text"])
        st.write("**Conversation thread**")
        render_messages(detail["messages"])

        with st.form("user_followup_form"):
            follow_up = st.text_area("Add a follow-up message", height=120)
            send = st.form_submit_button("Send message")
        if send:
            try:
                updated = add_follow_up(ticket_id.strip(), access_code.strip(), follow_up)
                st.session_state["ticket_detail"] = updated
                st.success("Message sent.")
            except requests.RequestException:
                st.error("Could not connect to backend.")
            except APIError as exc:
                st.error(str(exc))

elif page == "HR/Admin Dashboard":
    st.subheader("HR / Legal dashboard")
    admin_token = st.text_input("Admin token", type="password", help="Use the ADMIN_TOKEN from your environment.")

    if admin_token:
        col_a, col_b, col_c, col_d = st.columns(4)
        filter_status = col_a.selectbox("Status filter", ["", "OPEN", "UNDER_REVIEW", "RESOLVED", "CLOSED"])
        filter_category = col_b.selectbox(
            "Category filter", ["", "verbal harassment", "physical harassment", "digital harassment", "other"]
        )
        filter_severity = col_c.selectbox("Severity filter", ["", "LOW", "MEDIUM", "HIGH"])
        filter_department = col_d.text_input("Department filter")

        try:
            analytics = admin_analytics(admin_token)
            complaints = admin_list_complaints(
                admin_token,
                params={
                    "status": filter_status or None,
                    "category": filter_category or None,
                    "severity": filter_severity or None,
                    "department": filter_department or None,
                },
            )

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total complaints", analytics["total_complaints"])
            k2.metric("Open", analytics["by_status"].get("OPEN", 0))
            k3.metric("Under review", analytics["by_status"].get("UNDER_REVIEW", 0))
            k4.metric("High severity", analytics["by_severity"].get("HIGH", 0))

            chart_col1, chart_col2 = st.columns(2)
            with chart_col1:
                st.markdown("**Complaints by category**")
                if analytics["by_category"]:
                    category_df = pd.DataFrame(
                        [{"category": k, "count": v} for k, v in analytics["by_category"].items()]
                    ).set_index("category")
                    st.bar_chart(category_df)
                else:
                    st.info("No complaint data yet.")
            with chart_col2:
                st.markdown("**Daily submissions**")
                if analytics["daily_submissions"]:
                    daily_df = pd.DataFrame(
                        [{"date": k, "count": v} for k, v in analytics["daily_submissions"].items()]
                    ).set_index("date")
                    st.line_chart(daily_df)
                else:
                    st.info("No complaint data yet.")

            st.markdown("**Complaint queue**")
            complaint_df = pd.DataFrame(complaints)
            if complaint_df.empty:
                st.info("No complaints found for the selected filters.")
            else:
                st.dataframe(complaint_df, use_container_width=True)
                selected_ticket = st.selectbox("Select a ticket", complaint_df["ticket_id"].tolist())
                detail = admin_get_complaint(admin_token, selected_ticket)

                c1, c2, c3 = st.columns(3)
                c1.metric("Status", detail["status"])
                c2.metric("Category", detail["category"])
                c3.metric("Severity", detail["severity"])
                st.write(f"**Identity:** {detail.get('identity') or 'Anonymous'}")
                st.write(f"**Department:** {detail.get('department') or 'Unspecified'}")
                st.write("**Complaint text**")
                st.write(detail["text"])
                st.write("**Thread**")
                render_messages(detail["messages"])

                with st.form("admin_reply_form"):
                    reply_text = st.text_area("Reply to reporter", height=120)
                    reply_button = st.form_submit_button("Send admin reply")
                if reply_button:
                    updated = admin_reply(admin_token, selected_ticket, reply_text)
                    st.success("Reply sent.")
                    render_messages(updated["messages"])

                new_status = st.selectbox("Update status", ["OPEN", "UNDER_REVIEW", "RESOLVED", "CLOSED"])
                if st.button("Save status"):
                    updated = admin_update_status(admin_token, selected_ticket, new_status)
                    st.success(f"Status updated to {updated['status']}.")

        except requests.RequestException:
            st.error("Could not connect to backend.")
        except APIError as exc:
            st.error(str(exc))

else:
    st.subheader("About this project")
    st.markdown(
        """
        **SafeSpace Pro** is a hackathon-friendly but production-structured starter app for anonymous workplace harassment reporting.

        What it includes:
        - FastAPI backend with OpenAPI docs
        - Streamlit frontend for reporting, tracking, and HR review
        - Encrypted sensitive fields using Fernet
        - SQLite for local setup and PostgreSQL support for deployment
        - Scikit-learn text classifier for harassment category prediction
        - Threaded ticket-based follow-up using a one-time access code
        - Analytics dashboard for HR/legal teams
        """
    )
