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
version 1.2, wrapped Thai text, five article previews, web link and delivery ID.
Confirm that the chosen template consumes `attachments[].content`; adjust the
workflow mapping rather than assume every custom trigger accepts the same body.

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
The ID is visible in Teams and in JSON for receiver-side idempotency. The sender
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
