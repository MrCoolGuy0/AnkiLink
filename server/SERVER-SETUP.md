# Release 1.4.0 update

Group deck sharing requires the group_deck_shares server capability. The current
hosted and compatible standalone implementations support it without a schema
migration. See GROUP-SHARING-VALIDATION.md and hosted-server/SOURCE-PROVENANCE.json
for current tests and exact deployment identity. Earlier notes below describe
their named releases and must not override the current source provenance.

# Hosted service — no setup needed

AnkiLink 1.2.0 already uses the deployed service at
https://anki-link-evans.earthybox12.chatgpt.site.
Install the add-on, open Tools → AnkiLink, and create your own account using the
private invitation code provided in the release message. Both people use this
same server address and their own usernames/passwords. Exchange friend codes
after registration. No hosting, domain, Docker, Gemini key or AnkiWeb account
setup is required. See HOSTED-SERVICE.md for maintenance details.

The remaining instructions are an OPTIONAL self-hosted alternative. They do
not need to be followed to use the hosted service. Its 90 MB transfer limit
differs from the standalone server's configurable 250 MB default.

## Local check on one computer

With Python 3.11 or later installed, extract AnkiLink-Server-v1.2.0.zip and run:

```bash
python server.py --data data
```

Open Tools → AnkiLink and enter `http://127.0.0.1:8766` as the server address.
Create two sharing accounts in two separate Anki profiles for a local check.
The server has no Python package dependencies. It stores accounts/messages in
`data/relay.sqlite3` and attachments in `data/files`.

**That localhost address only works on that same computer.** Sending to your
partner over the internet needs the hosted HTTPS setup below.

## Internet hosting with Docker and a domain

Use a server/VPS that can run Docker, keep a persistent disk and accept inbound
ports 80 and 443. Point a domain/subdomain at its public IP address. Hosting and
domain availability/costs depend on the provider; no account or subscription
has been created by this package.

1. Put the extracted server files in one directory on the host.
2. Copy `.env.example` to `.env` and set:

   ```text
   ANKI_LINK_DOMAIN=link.yourdomain.com
   ANKI_LINK_JOIN_CODE=your-long-private-registration-code
   ```

3. From that directory run:

   ```bash
   docker compose up -d --build
   ```

The included Caddy service obtains/manages HTTPS for that domain. The relay's
port is available only inside the Docker network. Docker volumes retain the
relay data and Caddy certificates across container restarts.

Check `https://link.yourdomain.com/health`. It should report `AnkiLink` and
`1.2.0`. Then both users enter **https://link.yourdomain.com** in the add-on,
create accounts with the private registration code, and exchange friend codes.
Do not enter the `/health` suffix in AnkiLink's Server address field.

## Another container hosting provider

Deploy the included Dockerfile with persistent storage mounted at `/data`.
Route a public HTTPS address to container port 8766. Configure these environment
variables on the host:

| Variable | Value |
|---|---|
| `HOST` | `0.0.0.0` |
| `PORT` | `8766` or the provider-assigned internal port |
| `ANKI_LINK_DATA` | `/data` |
| `ANKI_LINK_JOIN_CODE` | Your private registration code |
| `ANKI_LINK_MAX_USERS` | `100` by default |
| `ANKI_LINK_MAX_FILE_MB` | `250` by default |

The provider must preserve `/data`; ephemeral-only hosting would lose messages
and accounts after a restart. Use `/health` for health checks. The client accepts
HTTPS addresses, with HTTP allowed only on localhost for testing.

## Keeping it running

- Back up the database and files together. Stop the relay briefly before copying
  the Docker data volume, or use SQLite's backup API plus a files backup.
- Preserve the data volume when deploying an updated server image.
- Sessions last fourteen days; passwords are salted PBKDF2 hashes. There is no
  email/password recovery service in this release. Keep your server backup.
- Images are limited to 12 MB; transfers default to 250 MB. Server storage usage
  depends on what your users upload. The relay does not bill a cloud API itself.
- This release is intended for a private invited group. Keep registration code
  private, maintain the host/HTTPS software and monitor available disk space.
- Messages are not end-to-end encrypted. The server operator can access the
  stored database/files; choose hosting you control and trust.
- The optional account registration code is different from each person's friend
  code. Friend codes connect already-created accounts; they do not grant host
  administration access.

These self-hosting steps are optional. The supplied hosted address already
works independently of this workspace; keep the invitation code private.


### Version 1.1.0 chat support

The standalone relay accepts WebSocket upgrades at `/v1/live`; Caddy's standard
reverse_proxy forwards upgrades. Retain the existing data directory. Startup
adds avatar, delivered/typing and per-session presence storage without removing
existing accounts/messages. The desktop retains REST fallback. Profile pictures
are private to friends/conversation members, and study deck activity is opt-in.


## Upgrade an existing standalone server to 1.2.0

Keep the existing data directory/volume and configuration. Replace the server
code and restart it (or rebuild the existing Docker service). Startup adds group
photo columns without replacing accounts, threads or messages. Do not delete
relay.sqlite3 or the files directory. The hosted default service is maintained
separately and does not require users to run these self-hosting commands.
