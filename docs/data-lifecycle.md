# User Data Lifecycle

This page describes the persistence behavior implemented in the current ScamShield repository and lists operational controls that must be reviewed before a public production launch. It is technical documentation, not a substitute for a jurisdiction-specific privacy notice or legal advice.

## What the application currently stores

| Data | Current behavior |
| --- | --- |
| Anonymous scan | The API can analyze a request without authentication. Anonymous scans are not written to the scan-history database. |
| Authenticated scan | When the request asks to save the result, the API stores the submitted content, scan type, score, verdict, analysis JSON, timestamp, and internal user ID. |
| Scan history and statistics | Read only records associated with the authenticated internal ScamShield user ID. |
| User report | An authenticated report stores its submitted content, reason, optional notes, timestamp, and internal user ID. |
| Provider identity link | Stores provider name, provider subject, internal user ID, optional email claim, and creation time. Matching email addresses do not automatically merge accounts. |
| Account-link intent | Stores a SHA-256 hash of a one-time token, target provider, user ID, expiry, usage time, and creation time. The raw link token is returned to the authenticated client and is not stored in the database. |

The account-link intent expires after ten minutes and is single-use. Provider identity tokens are verified by the API; the application database does not store the raw bearer token as an identity-link record.

## Retention and deletion status

The current API does not expose user-facing deletion controls or an automated retention cleanup job for scans, reports, identity links, or expired link-intent rows. Database backups and retention periods are determined by the deployment and database provider; they are not configured by this application code.

Do not promise users a deletion deadline or retention period until the deployment has implemented and tested the corresponding database and backup procedures.

## Pre-launch operational checklist

- [ ] Publish a privacy notice that accurately describes submitted content, authentication providers, hosting, and any optional third-party processing.
- [ ] Choose and document retention periods for scans and reports based on a reviewed product and legal requirement.
- [ ] Implement authenticated deletion/export workflows where required, including linked identities and dependent records.
- [ ] Define how deletion propagates to backups and how long backup copies remain recoverable.
- [ ] Add a scheduled cleanup process for expired one-time link intents if operationally appropriate.
- [ ] Restrict database access, encrypt connections, protect backups, and rotate credentials.
- [ ] Review whether optional AI explanation sends submitted content to an external provider; keep it disabled unless the disclosure and consent flow are appropriate.
- [ ] Test that users cannot read, update, or delete another user's records.
- [ ] Document incident response and a private vulnerability reporting path.

## Deployment notes

Use HTTPS for the frontend and API, configure CORS with exact trusted frontend origins, and keep provider secret keys, database credentials, service-role keys, and AI API keys server-side. Public browser configuration values must not be confused with server secrets.

Revisit this document whenever persistence fields, provider integrations, deletion behavior, AI processing, or hosting providers change.
