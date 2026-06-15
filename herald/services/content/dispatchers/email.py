import os
import logging

logger = logging.getLogger(__name__)

LEGAL_FOOTER = """
<hr style="border:none;border-top:1px solid #eee;margin:24px 0">
<p style="font-size:11px;color:#888;">
  This message was sent by [Bank Name]. Registered address: [Address].
  [Bank Name] is regulated by the Reserve Bank of India.
</p>
"""

UNSUBSCRIBE_BLOCK = """
<p style="font-size:11px;color:#888;">
  To unsubscribe from marketing communications,
  <a href="[UNSUBSCRIBE_URL]">click here</a>.
</p>
"""


async def send_email(payload: dict) -> dict:
    demo_mode = os.environ.get("HERALD_DEMO_MODE", "true").lower() == "true"
    content = payload["content"]
    ab_variant = payload.get("ab_variant")

    use_variant_b = (int(payload["customer_id"].replace("C-", "")) % 2 == 1)
    if use_variant_b and ab_variant:
        subject = ab_variant.get("subject_line", content.get("subject_line"))
        body = ab_variant.get("body_html", content.get("body_html"))
        variant_label = "B"
    else:
        subject = content.get("subject_line")
        body = content.get("body_html", "")
        variant_label = "A"

    body = body.replace("[LEGAL_FOOTER]", LEGAL_FOOTER)
    body = body.replace("[UNSUBSCRIBE_LINK]", UNSUBSCRIBE_BLOCK)

    if demo_mode:
        logger.info(
            f"[DEMO EMAIL] To: {payload.get('customer_email')}\n"
            f"Subject: {subject}\n"
            f"Variant: {variant_label}\n"
            f"Body preview: {body[:200]}..."
        )
        return {
            "provider_message_id": f"demo-{payload.get('outreach_id')}-{variant_label}",
            "variant": variant_label,
        }

    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail

    sg = SendGridAPIClient(api_key=os.environ["SENDGRID_API_KEY"])
    message = Mail(
        from_email=os.environ["SENDGRID_FROM_EMAIL"],
        to_emails=payload["customer_email"],
        subject=subject,
        html_content=body,
    )
    response = sg.send(message)
    return {
        "provider_message_id": response.headers.get("X-Message-Id"),
        "variant": variant_label,
        "status_code": response.status_code,
    }
