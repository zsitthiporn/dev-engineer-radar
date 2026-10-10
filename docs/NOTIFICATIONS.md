# Public digest delivery

The website is the reading destination. Notifications contain concise original
summaries and stable article URLs; details and primary references remain on the
site. `feed.xml` supports RSS readers and `feed.json` supports other integrations.

## Teams group chat (Workflows)

Use Teams **Workflows**, not a new legacy Microsoft 365 Connector. In Teams,
Workflows → choose **Send webhook alerts to a chat** (template names can vary),
select the intended existing group chat and authenticate the posting connection.
The workflow uses **When a Teams webhook request is received** and posts the
incoming Adaptive Card to the chosen chat. Add a co-owner so delivery does not
depend on one user's account staying active.

The sender implements the `type: message`/Adaptive Card attachment envelope,
version 1.2, wrapped Thai text and a compact preview of **every** edition article.
Confirm that the chosen template consumes `attachments[].content`; adjust the
workflow mapping rather than assume every custom trigger accepts the same body.

### Card presentation

An emphasized masthead shows the edition, article count and Try/Watch/Skip counts.
Each article has a numbered, clickable headline, a text verdict with a semantic
color, a separator, and a summary limited to 140 characters and two displayed
lines. Headlines also wrap to at most two lines. Long summaries use an ellipsis;
the complete text and primary references remain on the linked article. Editorial
text escapes inline Markdown syntax, and URL delimiters are percent-encoded before
building links. The generic JSON digest and its identity remain unchanged.

`msteams.width = Full` requests more space on desktop; stretch/auto columns keep
the verdict beside the heading. Teams controls fonts, colors, spacing and theme:
there is no custom CSS/HTML support for Adaptive Cards. Use semantic colors rather
than hardcoded RGB values, and retain verdict text so color is not the only cue.
No remote decorative image is required. Test on Teams desktop and mobile because
hosts can render Markdown and line limits differently. Schema/Designer validation
does not prove actual Workflows delivery or mobile rendering.

No articles are silently omitted to fit the message. If an edition exceeds the
24 KB sender budget, sending fails before the POST; split it into explicitly
reviewed messages or use the website. This adapter does not automatically split
an edition, which could complicate duplicate handling.

For this URL-only adapter, choose a template authentication setting that permits
the external sender (often **Anyone**); the signed URL acts as a bearer secret.
If organization policy requires authenticated callers, use a separately approved
Entra-authenticated adapter instead. Never weaken tenant policy just to use this
adapter. Store the URL directly in this repo's Actions secret
`RADAR_TEAMS_WEBHOOK`. Do not send it in chat, commit it, or put it into the frontend.
Rotate the workflow URL if exposed. Nothing reads an owner's credential files.

## Preview, then explicit sending

```console
python -m radar.notifications --date 2026-10-10 --output work/teams-payload.json
```

This default path has no network calls and does not read destination environment
variables. The manual **Preview or send radar digest** workflow behaves the same,
retaining the public card payload as a short-lived artifact. Inspect it first.
Set `send=true` only after confirming the destination and deployed article links.

For an owner-configured environment:

```console
python -m radar.notifications --date YYYY-MM-DD --send --destination-env RADAR_TEAMS_WEBHOOK
python -m radar.notifications --date YYYY-MM-DD --send --destination-env RADAR_ONE_WEBHOOK --destination-env RADAR_TWO_WEBHOOK
python -m radar.notifications --date YYYY-MM-DD --adapter json --send --destination-env RADAR_CUSTOM_WEBHOOK
```

The generic JSON adapter sends the versioned digest, not a Slack/Discord-native
payload. A custom receiver can route this digest to email, Slack, Discord or other
services; a native adapter and destination configuration are required for direct
delivery to those services. Multiple Teams Workflows endpoints work with repeated
destination arguments. The checked-in workflow selects one approved Teams secret;
additional channels require an explicit owner-configured workflow step/secret.

## Failure and duplicate semantics

All selected destinations are preflighted before any POST. HTTPS, no redirects,
public-address DNS checks, 20-second timeout and a conservative 24 KB payload budget
apply. DNS screening is defense in depth for trusted owner-configured URLs, not a
network-level DNS-rebinding guarantee. Missing secrets fail before sending.
No articles for an edition means no messages are sent.

A digest has a deterministic `deliveryId` based on its date and full public content.
The ID is in JSON, send logs and the Adaptive Card's plain-text fallback; it is
not shown in the normal card layout. The sender
does not promise exactly-once delivery or persist a delivery ledger. A 2xx response
only acknowledges the webhook, not that Teams successfully rendered the message.
No automatic POST retries: timeout/connection errors can mean the message arrived.
If a later destination fails, earlier acknowledgements stay in the run log; check
those chats and retry only failed destinations. CI concurrency avoids simultaneous
runs for the same edition but does not suppress an intentional rerun. A scheduled
fan-out should first add a receiver-side delivery ledger keyed by destination/ID.

URLs, tokens, error response bodies and raw exceptions from HTTP are not printed.
Only environment-variable destination names, delivery IDs and HTTP status are logged.
Automated tests use mocked delivery; live Teams delivery needs the owner-configured
workflow/chat and a deliberate test send.

## References

- [Teams incoming webhooks via Workflows](https://support.microsoft.com/en-us/workflows/send-messages-in-teams-using-incoming-webhooks)
- [Microsoft webhook/Adaptive Card documentation](https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/connectors-using)
- [Teams card formatting, Markdown and full-width cards](https://learn.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-format)
- [Adaptive Cards documentation and design guidance](https://adaptivecards.microsoft.com/)
