# AnkiLink

**Friends, chat, groups, and deck sharing — inside desktop Anki.**

[![Anki](https://img.shields.io/badge/Anki-desktop-1677ff)](https://apps.ankiweb.net/) ![Version](https://img.shields.io/badge/version-2.0.11-blue) ![Python](https://img.shields.io/badge/Python-add--on-3776ab) ![Status](https://img.shields.io/badge/status-active%20development-orange)

AnkiLink is a desktop Anki add-on that brings personal messaging, group conversations, and controlled flashcard-deck sharing into one workflow. Students can connect with friends, exchange messages and media, share decks, and review changes before importing content into their own collections.

The add-on is designed around **preserving each recipient’s existing Anki collection and scheduling choices**. Sharing a deck does not automatically grant another person control over their learning history.

> **Release:** v2.0.11 (desktop). **Package ID:** `anki_link`. **Minimum declared Anki version:** 23.12. This repository's source handoff includes both the desktop add-on and server-related projects; compatibility with every later Anki release and hosting configuration has not been independently verified here.

## At a glance

| Area | Capabilities |
| --- | --- |
| Accounts and friends | Account sign-in, invitation-code registration, friend codes, friend requests, profile images |
| Messaging | One-to-one chat, group conversations, text, emoji, images, animated media, stickers, saved messages and unread indicators |
| Group controls | Ownership and administrator roles, membership management, group activity notices, group photos, message reactions |
| Study presence | Online/idle status and optional sharing of the active review deck |
| Deck sharing | Select individual decks or hierarchies and deliver them to friends or groups |
| Receiver controls | Preview imports, choose destinations, protect local edits, choose whether to import settings or progress |
| Appearance | Default, AnkiRetro variants, AnkiRise, AnkiMessage, light/dark support, per-conversation chat colors |

## Features

### 1. Messaging and accounts

- Create or sign in to an AnkiLink account and connect with friends using friend codes.
- Exchange direct messages and participate in group conversations.
- Send text, Unicode emoji, supported images and stickers; open received images in a viewer.
- Receive unread indicators and system-tray notifications where supported.
- Read messages that arrived while you were disconnected when the client reconnects.
- React to messages, inspect who reacted, and change or remove your own reactions.
- Manage group roles and members according to owner/admin permissions; group changes create activity notices.

### 2. Deck sharing designed for Anki

AnkiLink transfers Anki decks with attention to structure, card identity, and receiver choice:

- Choose decks and nested children, or restrict the selection using Anki search.
- Share note content, required media, note types and selected card rows.
- Optionally include deck presets, per-deck overrides, learning steps, review limits, desired retention, and filtered-deck options when supported by the receiving Anki version.
- Keep the recipient’s learning progress by default; importing the sender’s progress is an explicit choice.
- Preview new and existing cards, updated notes, and conflicts **before** importing.
- Preserve the original deck hierarchy under a chosen destination in the receiver's collection.
- Update previously received decks without automatically duplicating the same card identities.
- Back up the Anki collection before an accepted import changes it.

**Important:** The receiver remains in control. New content, scheduling settings, learning progress, reset operations, and resolving local edits are separate decisions. For full behavior and known edge cases, see [VALIDATION.md](VALIDATION.md) and the historical notes in [CHANGELOG.md](CHANGELOG.md) when those files are included in the published repository.

### 3. Filtered decks and study settings

The transfer implementation accounts for filtered decks, captured card membership, parent/child hierarchy, two-rule filters, and Anki's native restrictions. When desired, receivers can import content without immediately rebuilding their practice decks.

AnkiLink **does not** automatically grade cards, intercept review ratings, or secretly reschedule your cards. It uses explicit, user-approved Anki operations when importing or resetting received material.

### 4. Personalization

Appearance choices in the v2.0.11 desktop source include **Default**, **AnkiRetro**, **AnkiRetro Baby Blue**, **AnkiRetro Maroon**, **AnkiRise**, and **AnkiMessage**. Recent updates also refine chat bubble colors, per-chat color selection, window styling and compact layouts. Theme support follows Anki's light/dark setting where available.

## Screenshots

Screenshots are not bundled into this README. Add screenshots of the actual interface under `docs/images/` and link them here to show messaging, group conversations, deck sharing and the appearance options. Avoid using screenshots containing real account details or private messages.

## Installation

### Install the packaged desktop add-on

1. Download the official `AnkiLink-v2.0.11.ankiaddon` file from a release you trust or from the source handoff you received.
2. In desktop **Anki**, go to **Tools → Add-ons → Install from file** (the wording can vary by Anki version).
3. Select the `.ankiaddon` file, then restart Anki.
4. Open **Tools → AnkiLink** or use **Ctrl+Alt+L** when the shortcut is available.
5. Create an AnkiLink account or sign in. New-account registration may require a private invitation code from the service operator.
6. Add a friend using their friend code and wait for acceptance before messaging or sharing decks.

**Do not upload the invitation code or any account credentials to a public repository.** The desktop package is distinct from the backend hosting configuration.

### Notes about platforms and hosting

- AnkiLink is a **desktop Anki add-on**. It is not an AnkiMobile or AnkiDroid plug-in.
- The desktop code contains a configured hosted-service endpoint. Running the standalone backend is optional for ordinary users of a working hosted deployment; server operators must use their own properly configured endpoint and credentials.
- Changing the server address does **not** automatically migrate accounts, messages, or files from another server.
- The server stores messages and attachments; **this is not end-to-end encrypted chat**. Server administrators with the appropriate access can access stored data.

## Usage guide

### Start a conversation

Open AnkiLink, sign in, add a friend's code, and accept the friendship request. Select a friend to begin a direct conversation. Use the group interface to create a conversation with accepted friends when needed.

### Share a deck

1. Open a conversation and select **Share decks**.
2. Choose the deck(s) and recipients; expand the hierarchy to select a smaller branch when applicable.
3. Review the optional deck-setup and learning-progress choices.
4. Send the deck invitation.
5. The recipient opens **View invitation**, reviews the import preview, chooses a destination and conflict handling, then explicitly accepts or declines.

### Update an already shared deck

Share the revised source again. When cards retain the same underlying Anki identities, the receiver can import updates without treating every previously received card as new. Local edits are surfaced for review rather than silently replaced.

## Project structure

```text
AnkiLink/
├── anki_link/                 # Desktop Anki add-on package
│   ├── __init__.py            # Add-on registration and startup
│   ├── dialog.py              # Desktop controller and UI integration
│   ├── transfer.py            # Deck/package transfer and merge logic
│   ├── config.py              # Profile-local configuration
│   ├── live.py                # Live/online status behavior
│   ├── net.py                 # Network transport
│   ├── notifications.py       # Desktop notifications
│   ├── media.py               # Media support
│   ├── avatar_crop.py         # Avatar image workflow
│   ├── manifest.json          # Add-on metadata
│   └── web/                   # JavaScript, CSS, and embedded chat UI
├── server/                    # Optional standalone Python relay
├── hosted-server/             # Hosting snapshots and deployment tooling
├── tests/                     # Python and JavaScript tests
├── build.py                   # Packaging and checksum tooling
├── SERVER-SETUP.md            # Standalone server instructions
├── HOSTED-SERVICE.md          # Hosted-service notes
├── VALIDATION.md              # Test/validation history
└── CHANGELOG.md               # Detailed release history
```

This tree is based on the v2.0.11 source handoff. Some directories or documents may not yet exist in the public repository until the full source is published.

## Development

### Desktop add-on

The desktop client is primarily **Python**, with an embedded **HTML/CSS/JavaScript** interface displayed using Anki's Qt-based UI. It integrates with Anki's collection and import APIs. Because the desktop client runs inside Anki, use an isolated Anki profile and test collection when developing transfer logic.

### Backends

The source handoff includes both an optional Python-based standalone relay and a separate hosted-service codebase containing TypeScript/JavaScript, deployment configuration, and database migrations. These are **different deployment paths**; do not assume that running one automatically restores production accounts, messages, or storage.

For setup and recovery details, consult `SERVER-SETUP.md`, `HOSTED-SERVICE.md`, and hosting-specific documentation in the full source tree. Never commit production `.env` files, private backups, account databases, or live storage credentials.

### Tests and packaging

Tests are included in `tests/`, including Python (`test_*.py`) and JavaScript (`test_*.cjs`) coverage for messaging, groups, permissions, transfers, configuration, and UI behavior. Some tests require Anki, Qt, live or local relay services, or special development dependencies.

The source includes `build.py` to package allowlisted files into the add-on installer and accompanying source artifacts. Review its command-line options before running it:

```bash
python build.py --help
```

**Validation disclaimer:** The source archive contains detailed test records, but this README's author did not independently execute the full Anki UI/server test suite or confirm the current hosted deployment.

## Privacy and security

- Use a dedicated Anki test profile for development and test imports.
- Review a deck invitation before importing another person's content.
- Do not upload private messages, invitation codes, account databases, authentication tokens, `.env` files or production storage backups.
- Account data, chat history and uploaded attachments live on the configured server. They are protected through service authentication/access controls, **not** end-to-end encryption.
- Publish deployment source carefully; production infrastructure settings and historical recovery material may contain operational details even when no password is embedded.
- If reporting a security issue, avoid posting private credentials or user data in a public GitHub issue.

## Known limitations

- Desktop Anki only; no native mobile companion is supplied.
- Some settings depend on the installed Anki version and the recipient's Anki/FSRS configuration.
- Filtered-deck membership and rebuild behavior remain subject to Anki's native constraints.
- A server migration requires separate planning for accounts and stored data.
- The code includes features introduced across multiple release series; availability depends on both desktop and server versions.

## Roadmap

Potential areas for future contributions include stronger setup documentation, additional accessibility testing, clearer first-run onboarding, improved cross-version compatibility checks, and broader automated testing. These are proposed directions, not promised features.

## Contributing

Issues and pull requests are welcome. For a good bug report, include your Anki version, operating system, how to reproduce the problem, and sanitized logs/screenshots. For changes to synchronization or deck imports, explain the effect on existing cards and scheduling, and include tests where possible.

**Repository:** [MrCoolGuy0/AnkiLink](https://github.com/MrCoolGuy0/AnkiLink)  
**Maintainer:** [MrCoolGuy0](https://github.com/MrCoolGuy0)

## License

An explicit open-source license is necessary to define what others may do with the code. **Do not assume the MIT license applies to the entire source handoff** until ownership and licenses for all included code and dependencies have been checked and an appropriate license has been committed. Third-party components keep their own licenses.

## Release history

The v2.0.11 handoff contains a detailed chronological history from early messaging and transfer versions through chat styling updates. See [CHANGELOG.md](CHANGELOG.md) for the original release notes, preserved rather than discarded from the earlier README.
