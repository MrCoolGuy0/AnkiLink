# Desktop 2.0.11 — Softer AnkiRetro palettes

Baby Blue pairs its blue frame with blue-lavender bubbles and a neutral chat pane. Maroon pairs wine and dusty rose with soft mauve and a neutral chat pane. Their chat swatches use the same color families in both light and dark mode.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.10 — Chat palettes for every appearance

Open a conversation's **⋯ → Chat color** for five presets matched to the active appearance. The reset swatch previews that appearance's default sent color. Your saved chat colors stay selected across appearance changes, and Custom still accepts any color.

AnkiRetro Baby Blue pairs blue with peach and lilac. AnkiRetro Maroon pairs maroon with sage and parchment.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.9 — AnkiRetro color variants

Choose **AnkiRetro · Baby Blue** or **AnkiRetro · Maroon** in **Profile → Appearance**. Both use the original AnkiRetro layout and follow Anki's light or dark mode.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.8 — Classic AnkiRetro

AnkiRetro now uses pink window panels, raised square controls, and a plain chat pane with blue received bubbles and pink sent bubbles. The Windows title bar is deep blue. The composer puts Send above the image, emoji, and sticker buttons, with typing status below.

Decorative stars, clouds, and deck patterns are gone. This appearance supports light and dark mode and your existing chat colors.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.7 — AnkiMessage refinements

AnkiMessage uses shorter, rounded tails on incoming and outgoing text bubbles. In the narrow chat view, the conversation title, avatar, and status stay centered. The Share decks button uses a folder icon with a tooltip, and Conversation options stays beside it.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.6 — Curved AnkiMessage tails

AnkiMessage text bubbles now have tapered tails that follow the bubble color in light and dark mode.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.5 — AnkiMessage

Choose **AnkiMessage** under **Profile → Appearance** for a Messages-inspired sidebar, centered contact header, round avatars, and green sent bubbles. The theme follows Anki's light or dark mode and supports existing per-chat colors. Search in the sidebar filters conversations by name or preview text.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.4 — Connected AnkiRise chat pane

AnkiRise uses one outline around the contact header, message history, and composer. The scrollbar has a slim teal track inside the frame, with space between the track and messages.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.3 — AnkiRise

Choose **AnkiRise** from **Profile → Appearance** for pale blue grid paper, teal outlines, and deck cards styled like small desktop windows. It follows Anki's light or dark mode. AnkiRetro has simpler group notices and a cleaner sidebar with more room for conversations.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.2 — AnkiRetro appearance option

Open your profile menu and choose **Appearance**. **Default** restores the original AnkiLink interface. **AnkiRetro** uses the pink and lavender design, with the blue native title bar on supported Windows systems. Your choice is saved for the current Anki profile and applies immediately.

Direct messages show time and delivery information under the bubble. Group chats also show the sender name for incoming messages.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.1 — Full-window chat

The chat fills the window. The outer wallpaper, “Study together” footer, and version badge have been removed. On Windows 11, AnkiLink colors the actual window title bar blue, with the flower icon and standard window controls. The native caption is used when custom coloring is unavailable.

Install this update over AnkiLink and restart Anki.

---

# Desktop 2.0.0 — Retro AnkiLink

The desktop chat now has an iridescent frame, pink and lavender panels, an illustrated retro computer, and a cloud header. The navigation has clear chat, friend, and deck icons. Shared decks appear in heart-patterned cards, and dialogs use the same beveled window style.

The compact dock uses a single pane with a smaller frame. Anki's dark mode selects a darker retro palette, and chat colors still apply to your outgoing bubbles. Illustrations are small, bundled SVG files.

Install the complete add-on over your existing AnkiLink and restart Anki. This release is compatible with hosted service 1.5.2. The continuation ZIP includes the desktop source, artwork, and deployed server snapshot.

---

# Desktop 1.5.5 — background online and study status

AnkiLink connects when Anki opens a profile with a remembered Windows sign-in, even if the chat window is never opened. Friends can see Online or Idle while Anki runs. Turn on **Share study activity** in the account menu to show the current native review deck. Only the final part of its name is shared.

Presence refreshes independently of chat sync. The hidden window uses a slower timer, repeated reviews in the same deck reuse its name, and the backup connection keeps only one presence request in flight. When the chat window first opens, it can show friend status already received in the background.

Install over the existing add-on and restart Anki. This desktop release works with hosted service 1.5.2. The continuation ZIP includes the current desktop source and the deployed server snapshot.

---

# Desktop 1.5.4 — profiles in reaction names

The reaction viewer now shows each person's profile photo, display name and username. Missing or still-loading photos show initials and refresh automatically when the image arrives. A compact emoji/count summary, consistent 40px portraits and a quiet You badge provide clear spacing and hierarchy in both themes. Long names wrap inside the list.

Reaction behavior is unchanged: chips show people; your current emoji in the picker removes your reaction. No hosted service or data changes: service 1.5.2 remains deployed. Top-level client/tests contain desktop 1.5.4; nested exact-hosted-source is the deployed server snapshot. Every update includes the installer and complete continuation ZIP. Install and restart Anki.

---

# Desktop 1.5.3 — view reaction names

Click a reaction chip below a message to see the people who chose that emoji, including display names and usernames. Viewing sends no reaction request. To remove your reaction, open the emoji picker and select your current emoji again. The name list refreshes as reactions change and closes when access to the group is removed.

Installer and full continuation ZIP include this client update. Hosted service remains the verified 1.5.2 deployment; no server, account, schema or data changes. The top-level anki_link/ and tests/ contain desktop 1.5.3; hosted-server/exact-hosted-source/ is the unchanged deployed server snapshot. Install and restart Anki.

---

# Release 1.5.2 — immediate reactions and personal chat colors

Reactions update immediately without a loading overlay. Rapid changes queue in order per message; failed final updates return to the last confirmed reaction with an error. Server reaction versions still reject stale replies.

Adding, replacing or removing a group photo creates a durable activity line naming the actor. Identical retries create no duplicate line. The update and notice commit together. Existing group permissions and quiet desktop behavior remain.

Conversation options → Chat color contains compact presets, a custom color picker and a default reset. Colors affect only the open chat on this account/device, persist across restarts, and use readable light/dark blends. Layout and message nodes remain stable.

Same host, accounts, database and private files; no schema migration. Install and restart Anki. Every update includes the installer and complete matching continuation ZIP. Keep private data backups separate. Backup/recovery accepts 1.5.2 as well as earlier supported versions. Exact deployment identity is in hosted-server/SOURCE-PROVENANCE.json.

Validation: immediate/queued reactions and HTTP failures; saved/account-isolated colors and invalid input; group-photo actor notices and duplicate suppression on both backends; native light/dark geometry at 300/420/820px; retained relay, export and recovery regressions.

Earlier release notes below are historical.

---

# Release1.5.1 — compact controls and group activity

The reaction add button sits beside its message; chips stay close to the bubble. The floating picker closes on outside click, Escape, scrolling, navigation or another dialog, and does not add chat spacing. Group member actions are inside per-person ⋯ menus with the same authorization and removal confirmations.

Durable group activity lines show who added/removed members, changed admins, left, and became the new owner. They use server-generated name snapshots, cannot be submitted as ordinary messages, and do not have reaction or delivery controls. Notices and membership changes commit atomically; failed and no-op actions do not create misleading entries. Activity lines do not create desktop notification popups.

No schema migration or account reset is included. Update/restart all desktop clients for correct system-line rendering. Same service/DB/private attachments. Both the complete installer and matching full source continuation ZIP must accompany every update. Current backup and recovery support patch1.5.1 and retain the new activity records.

Validation: seven DOM scripts; real native Qt light/dark geometry at300/420/820px, pointer and keyboard dismissal, viewport and scrolling bounds; hosted atomic-notice/concurrency/rollback tests; standalone HTTP/WebSocket notice tests; existing desktop two-user and Python regressions. Exact successful deployment identity is in hosted-server/SOURCE-PROVENANCE.json.

Earlier release notes below are historical.

---

# Release 1.5.0 — reactions and group administration

Current host: https://ankilink-jm.jdgarcia2697lag.chatgpt.site (same project, DB and private BUCKET).

Messages support 👍 ❤️ 😂 😮 😢 😡 🎉 reactions. Each member can add, change or remove their own reaction. Group creators become owners. Owners can appoint/demote admins; owners/admins can add accepted friends and remove members within their permissions. Owners are protected from removal. Leaving as owner randomly transfers ownership to a remaining member; leaving as the final member archives the inaccessible conversation without deleting its history. New members can see existing group history.

The owner explicitly selected jigstar as owner for existing groups containing that account. Other legacy groups require an explicit owner assignment and are not silently given to another user. Legacy owner assignment is enabled temporarily by ANKI_LINK_LEGACY_OWNER_USERNAME and is disabled afterward.

The update adds schema and preserves existing account IDs/passwords, conversations, attachments, settings, transfer receipts and Anki scheduling. Everyone should install the update and restart Anki. Old compatible clients retain normal messaging but do not display the new controls.

Every add-on update must include the complete .ankiaddon AND complete matching source/continuation ZIP. Keep private live-data backups separate from code archives. New backups must include owner/admin fields, message_reactions and reaction_updates; old backups predate later messages, password resets and new group/reaction state. Read CONTINUE-HERE.md and REACTIONS-GROUPS-VALIDATION.md.

Earlier release notes below are historical.

---

# Release 1.4.1 — hosting restored under the current account

Server address: https://ankilink-jm.jdgarcia2697lag.chatgpt.site

This installer preserves package identity `anki_link` and automatically migrates only the two previous official addresses. Existing custom servers are unchanged. It preserves saved sign-in, device identity, imported-deck receipts, lineage, last-shared tracking, account-specific mute/activity settings and sticker IDs. The server restores the owner-approved snapshot from 1 November 2026: 15 accounts, 150 messages and all 24 uploads. Existing account IDs, password hashes, friend codes, groups and invitations are retained. The previous host is a separate service and cannot be shut down through this account; all members should install this update and restart Anki together.

The exact v1.4.0 relay application and original database migrations are unchanged. The new host uses the supplied portable Worker approach with persistent DB and private BUCKET bindings. The temporary restoration entry is excluded from the final deployed bundle and its authorization settings are removed after verification. New registration uses a new private join code; existing accounts sign in with their existing password.

Every release must provide BOTH the complete installer and complete matching continuation ZIP. See CONTINUE-HERE.md and DELIVERY-REQUIREMENTS.md. Private backups and secrets are separate from source archives.

Historical documentation below describes earlier releases and hosts.

---

# AnkiLink 1.4.0 — group deck shares and stable conversation menus

Install the complete AnkiLink-v1.4.0.ankiaddon over the existing add-on and
restart Anki. The matching AnkiLink-Full-Source-v1.4.0.zip includes the desktop
client, compatible standalone server, exact hosted service source, dependency
lockfiles, migrations, tests and continuation/deployment instructions. Preserve
package ID anki_link. Read DELIVERY-REQUIREMENTS.md before future changes.

Share decks from a group conversation to post ONE deck card in that group.
The destination appears explicitly in the share dialog. The server derives
current members rather than expanding them into private chats. Every other
member receives their own invitation and can accept or decline independently.
Retrying the same share does not add messages, invitations or reset decisions;
starting a new share sends the later update. Ordinary private/multi-friend
sharing remains available outside group sharing.

New group sharing requires the server's group_deck_shares capability. An older
server produces a clear error before export/upload; there is no private-message
fallback. The existing hosted server is updated in place through its retained
project. No database migration, account reset or attachment relocation is needed.
See hosted-server/SOURCE-PROVENANCE.json for the exact deployment delivered.

The retained hosting project now reports https://anki-link-evans.begrgbrgbrt.chatgpt.site as its canonical address.
The installer migrates only the previous official earthybox12 address. It retains
saved sign-in, identity, transfer receipts, account-specific mute/activity settings
and sticker lists. Custom server URLs are unchanged. All members should install
this update and restart Anki; no new account or chat reset is needed. This is an
address change within the same project and DB/R2 bindings, not a new server.

The Share decks action is pinned to the right in group and private headers.
The group title now takes the flexible space and truncates safely. Conversation
menus retain their DOM and focus during chat updates. Dialog background blur is
removed, and focus stays in the dialog until it closes, returning to its trigger.
The translucent backdrop, existing layout, colors, controls and drafts remain.

Tests cover group membership/file ACL, one shared post, independent decisions,
concurrent retries, old-server failure, explicit group/private destinations,
late replies, history invitation metadata, sign-out isolation and modal focus.
Real Qt WebEngine/controller/HTTP/native-Anki integration covers export, group
message preview, import of filtered decks with rescheduling off, presets/new-card
limits, unchanged source card rows, window/sidebar layouts, light/dark themes,
repeated notification-menu use, images/stickers, mute and exact-thread notices.
See GROUP-SHARING-VALIDATION.md for evidence and verification limits.

Source ZIPs contain code, not your live chats/accounts/uploads or Windows profile
state. The running service's data must be backed up separately before a move.
No real messages, test accounts or deck shares are sent to the production service
as part of testing. Existing chat/deck data and scheduling are preserved.

# Historical notes

# AnkiLink 1.3.0

A separate desktop Anki add-on for private study chat and deck invitations.
Install alongside Study List, Cram and Study Sounds. It does not replace them.

## 1.3.0 — resizable sidebar and compact message notifications

Install the full update over AnkiLink, then restart Anki. No server update,
new account or change to the other add-ons is required.

- **Ctrl+Alt+J** or **Tools → AnkiLink sidebar** shows/hides a dock on the right.
  Drag its left divider to change width. The last width is saved per profile.
- Narrow widths show one pane: chats, the selected conversation, or shared
  decks. The chat back arrow returns to the list. Widening the dock shows the
  chat list and conversation side by side. Forms, modals and the composer adapt.
- **Tools → AnkiLink / Ctrl+Alt+L** retains the separate normal window, including
  minimize/maximize/close. The sidebar's ↗ button opens that same window.
  Both presentations use one live WebView: draft, conversation, loaded images,
  scroll position and pending operations stay in that page when switching.
- New incoming messages show one small notice inside Anki, without taking
  keyboard focus. Click its body or **Open** to visit that exact conversation.
  **Mute** silences that conversation immediately; **×** dismisses the notice.
  Messages, images, stickers and deck invitations have appropriate previews.
- Muting is saved per Anki profile and AnkiLink account/server. Open a chat's
  **⋯ → Message notifications** to turn its alerts back on. Muting does not stop
  messages, change read status, or accept/import any deck.
- Notices expire after 6.5 seconds, pause on hover and resume on leaving. Bursts
  replace the single notice instead of filling the screen. Existing unread
  history on sign-in, own messages and duplicate live/poll updates do not alert.
  A focused open conversation stays quiet. Notices are child widgets inside
  Anki, not desktop popups when Anki is minimized or behind another application.

No review, queue, scheduler or transfer rules changed. Network work remains
outside Anki's collection executor. Background connections and the earlier
explicit action progress indicators remain intact.

## 1.2.2 — normal minimize and restore

AnkiLink now opens as its own non-modal window with normal minimize, maximize
and close controls. Use the title-bar minus button to minimize it, then restore
it through the operating system taskbar/window switcher, AnkiLink tray icon, or
the existing Tools → AnkiLink / Ctrl+Alt+L action while using Anki. Minimize does
not minimize the main Anki window. The same WebView, conversation and unfinished
draft stay in memory; opening the existing window does not recreate it.

The previous window explicitly enabled Maximize but omitted Minimize. That was
a window-configuration oversight, not a deliberate performance restriction.
Closing X already hid the window while leaving its connection active. It still
hides on X, and the Anki profile controller cleans up the independent window
when the profile closes. No new app, account or server is required.

A minimized window uses the existing background refresh path: slower periodic
bootstrap checks and live pulls, with normal delivery/reconnection still active.
It cannot mark messages Seen while minimized. Restoring returns to the ordinary
foreground cadence. HTTP/media work remains outside Anki's serialized collection
worker; minimizing is not a guarantee of zero memory/network/CPU use.

Install this complete update over AnkiLink and restart Anki. The existing shared
service and standalone server remain 1.2.0. Group members/photos, silent routine
refreshes, chat, deck merging and the established page layout are retained.

## 1.2.1 — silent background refreshes

Routine refreshes now run without a loading spinner in Chats/Friends/Decks.
Messages, member/photo changes and friend/deck updates continue to refresh at
the existing cadence. Explicit actions such as creating a group, adding a
friend or sharing decks retain their own progress, duplicate-click protection
and error handling. Routine refresh completion cannot clear a pending action.

Sharing only Midterms::Science::Lesson 3 already carries Midterms and Science
as ancestor containers, without selecting Lesson 1/2 or unrelated parent cards.
The recipient gets the full hierarchy, not a top-level Lesson 3. With Merge into
existing decks checked, a later Science share reuses those parent decks and the
same Lesson 3 card identities, while adding Lesson 1/2. This transfer behavior
was verified with actual disposable Anki collections; the transfer engine was
not changed. Keep deck names/paths and card identities consistent for merging.

Install this complete update over AnkiLink and restart Anki. The existing shared
service and optional standalone server remain 1.2.0; no server update is needed.
All group-member/photo features and existing chat/deck-sharing behavior remain.

## 1.2.0 — group members and shared photos

Open a group conversation, then click its **name or photo** at the top to open
**Group details**. The panel lists every member by name/username and marks your
own entry with You. Choose **Change photo** to select and crop an image, or
**Remove photo** to restore the group's initials. Any current member can change
or remove the shared group photo. Your personal profile picture is separate.

A local square crop previews before upload. Preparing, Uploading, Saving and
Saved states show what is happening; failed saves offer Retry. Closing and
reopening the panel keeps the in-progress state. A confirmed picture appears
in the chat list, conversation header and group panel. Photo revisions prevent
old snapshots/live frames from undoing a later saved photo or removal. Other
members receive live metadata hints and ordinary refresh/reconnect catch-up.
The member list and colors use the existing interface in light and dark mode.

Install this full update over AnkiLink and restart Anki. The default shared
service has also been updated; keep the same server address and accounts.
Each person needs this desktop release to use the new group controls. Optional
self-hosted users must also update their standalone server to 1.2.0, retaining
its data directory. The new columns are added without deleting existing rows.

The server checks group membership, image ownership, MIME type and size. Group
photos are private to their uploader and authorized group members unless that
same file was explicitly shared through another existing feature. Accepted
friends outside the group do not gain access just by being friends. Changing
a group photo does not touch Anki decks, scheduling or personal profile photos.
The previous group-freeze/loading fixes, chat, deck transfers and UI remain.

## 1.1.3 — group freeze and visible action progress

Install the full update over AnkiLink and restart Anki. No server update or
new account is required. This is the complete add-on, including prior features.

Creating a group could stop the list and navigation from rendering. A group
avatar has a name but no user ID. The previous optional-ID comparison evaluated
true when both IDs were absent, then read a missing profile editor object.
Group avatars now render without requiring an active profile-picture edit.

Group creation, friend requests/acceptance, opening conversations, deck listing,
sending, previewing and importing now track their own pending request. Their
controls show progress, duplicate submissions are disabled, and the dialog's
Close button stays usable. Pending tabs have a small spinner. Closing a dialog
keeps the request running; its late result cannot close a different dialog or
move you away from the tab/conversation you selected. Failures restore the
relevant controls and show the error. Read-only deck loading can be reopened
without starting the same request twice. A bootstrap no longer falsely closes
a pending friend request before the server confirms it.

Deck sharing shows Preparing decks, Uploading decks, then Sending invitations.
Preview shows Downloading shared decks, then Checking shared cards. Export and
preview use their own status instead of a global native progress dialog; their
collection reads remain serialized QueryOps. Only explicitly accepting a deck
uses the existing collection-changing import route and options.

A forced refresh arriving during an older snapshot now schedules one immediate
follow-up rather than being discarded. Switching tabs requests fresh data. Unchanged refreshes retain navigation
nodes and keyboard focus.
The open window refreshes social lists about every three seconds; the hidden
window uses a slower interval. Network response time still applies. Small
images/stickers use the media connection pool, and at most two queued images
occupy workers, leaving chat/group/friend requests available. This does not
promise instant delivery on every connection.

The package identity, existing layout, chat history, accounts, native review
worker isolation, deck merge/settings/progress choices and other add-ons are
preserved. Hosted and standalone server code remain 1.1.0. The matching handoff
ZIP contains this exact installer, source, regression checks and release notes.

## 1.1.2 — keep network jobs out of the review worker

Install the full update over AnkiLink and restart Anki. HTTP polling, image
preparation, uploads and downloads now explicitly use Anki's non-collection
worker pool. The former default shared the single collection worker: a slow
request could delay the next native card even with the chat window hidden.
Actual catalog/export/import operations retain Anki's serialized collection
operations. Success/failure, profile-epoch guards, live messaging, crop/profile
feedback, deck merging and UI are retained. The existing hosted/standalone
server remains 1.1.0; no server deployment or account change is needed.

Short tests reproduce the former blocked-next-card case and verify the fixed
worker split. A local probe with the unmodified Anki25.9.2 TaskManager and real
Qt signals confirmed it, including main-thread completion. This identifies a
concrete cause but does not diagnose every add-on or the user's PC.

## 1.1.1 — profile cropping, feedback and connection reuse

Install the full update over AnkiLink and restart Anki. The existing hosted
server stays 1.1.0 and the account/server address remain the same.

Set profile picture now shows **Preparing**, **Uploading**, **Saving** and a
confirmed **Saved** status. The resized image previews locally before upload;
background updates cannot revert this preview. Confirmation reuses its image
node instead of flashing/re-downloading the photo. Only profile controls are
disabled while saving; closing and reopening Account keeps the current status.
Before uploading, a local crop window lets you drag to reposition, zoom, Reset or Cancel. Only the accepted square 256px crop is uploaded. The original stays intact.
Cancellation restores the saved picture. Failures restore the saved picture
and offer Retry where possible. If upload succeeded but saving timed out, Retry
reuses the uploaded file. Profile requests use the already pooled background
HTTP connection instead of forcing a cold chat/API connection. The composer icons use clean symmetric geometry. Repeated native card events coalesce activity updates and cache the current deck name briefly, avoiding a deck lookup and network request per card. Upload and server
save time still depend on the connection; a preview is not a save confirmation.

## 1.1.0 — live chat and study presence

Install this full update over AnkiLink on both computers, then restart Anki.
The existing server address, accounts, chat history and deck merging stay.

- Messages and stickers use a persistent authenticated connection. Background
  refreshes do not hold message writes. Local text bubbles appear immediately;
  chosen images/stickers show a preview while uploading. Upload time and network
  latency still apply. This is not a zero-latency delivery guarantee.
- **Sent**: saved by the server. **Delivered**: received by another member's app.
  **Seen**: that member opened the conversation while visible, focused and near
  its latest message. Groups show partial counts. Older clients need updating
  to send delivery acknowledgements.
- Typing uses three subtly animated dots. Brief refreshes retain their animation
  nodes; the indicator expires after typing stops or a connection is lost.
- In the bottom-left account **⋯**, choose **Set profile picture** (or Remove).
  Images are resized to a small static profile photo; the source file is kept.
- In that same account panel, turn on **Share study activity**. It is off by
  default. Friends/conversation members see **Studying Lesson 1 Cardiology**,
  using only the current deck's final name. Otherwise the status is **Online**,
  **Idle** after five minutes without input, or **Offline** after expiry/sign-out.
  Activity reads the current native Anki/ANKI CRAM review card; it never answers
  cards or changes scheduling. Independent MAIN CRAM is not tracked as a native
  review session. Remembered Windows sign-ins reconnect when the profile opens.
- Connection loss triggers reconnection and persistent message catch-up. A lost
  acknowledgement retries with the same nonce; retrying cannot create another
  copy of that same message. HTTP remains available when live upgrades fail.

## 1.0.7 — merge received decks into the existing hierarchy

Install over the existing AnkiLink and restart Anki. The receiver needs this
update. Resend SEPC as a new invitation, then accept with **Merge into existing
decks** checked. Leave **Reset received cards to New** unchecked to keep progress.

Merging is the default for a new sender. It imports directly into matching full
deck paths, such as MIDTERMS::SEPC::Lesson 1, reusing parents/lessons and adding
new cards and sibling lessons. Repeated sends update matching note identities
and do not duplicate those cards. Existing local note edits keep the previous
conflict choice: they stay unless explicitly replaced. Settings and copied
progress remain independent choices; applying settings can also update matching
parent deck settings. FSRS consent and explicit reset choices are unchanged.

To keep received decks separate, uncheck Merge into existing decks and enter a
destination folder. The choice is remembered per sender. Existing old clients
remain compatible, but their receiver UI still uses the separate-folder mode.

Resending in merge mode also consolidates selected cards from earlier AnkiLink
imports, including a received lesson the receiver manually dragged elsewhere.
Empty prior folders are removed only after checking that they have no cards,
borrowed cards or child decks. Other cards and unrelated branches remain. A
partial resend remembers the old sender folder for later lessons. Existing
unrelated filtered rounds retain membership/progress; requested received-filter
rebuilds use the merged hierarchy. Native backups precede collection changes.
Already accepted invitations are not re-imported automatically: send again to
repair the older hierarchy. No manual deletion of card-containing decks is needed.

Matching cards uses Anki note GUID plus card ordinal. Independently recreated
copies with different identities are not merged just because their text is
similar. Exact full deck paths are matched; equal lesson names under different
subjects are separate. Renamed custom target paths are not guessed.

The chat/sticker speed improvements, Windows file-lock fix, existing styling
and other add-ons remain. No hosted server change or new account is required.

## 1.0.6 — faster actual delivery and sticker creation

Install over the existing AnkiLink add-on and restart Anki on both computers.
The hosted server was also optimized in place; the address, invitation code,
accounts, messages and storage remain the same.

The previous network client repeatedly opened fresh TLS connections. The new
client retains an authenticated connection pool across operations and reuses
the sign-in connection. Brief requests reuse one warm connection; large files
use a separate pool so a deck transfer cannot occupy the chat connection.
Anki's bundled requests dependency is used, including normal proxy support.
Redirects are still blocked, machine .netrc credentials/cookies are not used,
and message POSTs are never silently retried. Account/server changes replace
and close the old pool. Profile shutdown closes both pools.

Foreground messages are checked about once per second and only new messages
are fetched after initial history. Sidebar refresh is throttled independently;
explicit friend/group actions and Refresh still refresh immediately. Hidden
window polling remains eight seconds. A discarded reply for an inactive chat
does not advance its history cursor; reloading the page resets cursors.

New static stickers fit within 512 x 512 pixels, preserve aspect ratio and
transparency, and use WebP with PNG fallback. Original files are unchanged.
Animated GIF/WebP/APNG remain animated and retain their original bytes. Your
uploaded stickers have an account/server-scoped, hash-verified local cache.
Successful image/sticker creation displays the uploaded bytes and confirmed
message directly, without downloading your own upload or waiting for another
poll. Ordinary image uploads retain their original resolution/bytes.

The hosted relay batches message insertion/ID lookup, reads rate counters in
their atomic update, joins attachment metadata into message reads and combines
file-permission lookups. Membership/ownership checks, rate limits, private file
access and message idempotency are retained. No database migration is needed.

The first connection and a new file upload still take real network time; this
release removes repeated handshakes and extra round trips. All previous UI,
Sending…/Retry handling and the Windows deck-transfer fix are retained.

## 1.0.5 — responsive chat sending

Install over the existing AnkiLink add-on and restart Anki on both computers.
No server setup, account reset or redeployment is required.

Text sends now clear the composer immediately and show a Sending… bubble.
The server's write acknowledgement confirms that bubble directly, without
waiting for bootstrap and a second messages fetch. You can type and queue the
next message immediately. Writes in one conversation stay ordered; separate
conversations can send independently. Built-in and saved stickers use the same
pending/confirmation flow. Image uploads keep their existing upload behavior.

Failed sends retain their original content in a Not sent bubble with Retry.
Retries reuse the original nonce so a timeout after server acceptance cannot
create a duplicate. Polling can confirm a message before its send reply; late
replies/failures cannot duplicate it or erase a newer draft. Other errors do
not mark an unrelated pending message as failed. Existing received image nodes
stay in place during ordinary appends and pending/confirmation updates.

Chat-message polling runs independently of account/sidebar refresh, including
when opening another conversation while a refresh is already in flight. Read
receipts no longer launch another immediate full refresh. Actual server/network
response time still applies; Sending… is not a claim of server acceptance or
recipient delivery. Pending drafts/messages stay in this running window, not a
new durable offline queue; signing out or restarting clears unsent state.

The 1.0.4 Windows export/import cleanup fix is retained. Existing interface,
server URL/code, accounts, chats, sharing choices and other add-ons are retained.

## 1.0.4 — Windows deck-transfer file locks

Install over the existing AnkiLink add-on, fully quit Anki and reopen it.
Update both sender and receiver for the sending and receiving cleanup fixes.

Fixes WinError 32 on a temporary copy.anki2 while sending decks. Python's
SQLite transaction context commits/rolls back without closing the connection;
Windows therefore refused to remove the temporary database. Export cleanup,
received-package preview and import preparation now explicitly close each
SQLite connection before removing its temporary folder, even on errors.
No garbage collection, sleep/retry or suppressed cleanup errors are used.

The server address, existing accounts/chats, invitation code, sharing choices,
UI and other add-ons stay unchanged. No server setup or redeployment is needed.

## 1.0.3 — consistent button colors

Install over the existing AnkiLink add-on, fully quit Anki and reopen it.
The server, account storage and invitation code stay unchanged.

Anki's default toolbar stylesheet could paint a white gradient over AnkiLink
buttons while leaving their text white, including Sign in. AnkiLink now opts
out of that toolbar CSS and supplies scoped control states in controls.css.
Primary buttons retain a purple background and readable text; secondary,
icon, tab, conversation, emoji/sticker and text buttons use matching theme
tints on hover/press. Keyboard focus has an accent outline. Disabled buttons
retain their own colors. The image viewer keeps a readable close control over
its dark overlay, independently of the app theme. Both light/dark themes are
covered. There is no geometry-changing hover animation or global Anki styling.

Login/registration, empty state, sidebar, friends, deck invitations, chat,
composer, pickers, account/share/import dialogs and image viewer use the same
control rules. Layout, button actions, bridge, chat and deck-transfer logic are
retained. Other add-ons and Anki's own interface are not changed.

## Ready to connect

The shared server is now hosted at:
https://anki-link-evans.earthybox12.chatgpt.site

Its address is already filled in. You do not need to run a server, enter an API
key, or connect an AnkiWeb account. Each person creates their own AnkiLink
account using the private invitation code supplied with this release, then adds
the other person's friend code. The invitation code is deliberately excluded
from the installer and source archives. Existing custom server addresses stay
unchanged; blank addresses use the hosted service.

Version 1.0.2 fixes the remaining local startup failure. The window now
registers its handler AND context with Anki's set_bridge_command before loading
the page. stdHtml's rendering context does not register incoming pycmd messages.
Previously these messages were ignored, so 1.0.1 eventually showed "could not
connect to Anki" even with a reachable server. The window owns its handler;
there is no global AnkiLink message hook. Other windows' messages are rejected.

The DOM-ready gate, bridge timeout/Retry, explicit UTF-8 files, hosted default,
existing sharing UI and features remain. The server address and invitation
code from 1.0.1 are unchanged. No server setup or account reset is required.
The optional standalone server is included; see SERVER-SETUP.md and
HOSTED-SERVICE.md.

## Install and open

- Desktop Anki 23.12 or later: Tools → Add-ons → Install from file.
- Select AnkiLink-v1.1.1.ankiaddon and restart Anki.
- Open **Tools → AnkiLink**, or **Ctrl+Alt+L**.
- Select Create account and enter the supplied invitation code. Add a friend
  using the friend code below their account name.
- Accept the friend request before sending a direct message or deck.

## Chat

- Private conversations and groups made from accepted friends.
- Enter sends; Shift+Enter inserts a line break. Unicode text and emoji are
  preserved. The smile button opens an emoji picker; emoji appearance uses the
  operating system's emoji fonts.
- The image button sends PNG, JPEG, GIF or WebP, up to 12 MB. Pasting an image
  into the message box sends the clipboard image as PNG.
- The sticker button includes eight built-in study characters and an **Add an
  image sticker** option. Uploaded stickers are kept in your own sticker picker.
  Animated GIF/WebP files retain their uploaded format.
- Click a received image to enlarge it; X or Escape closes it.
- Messages are saved on the server. An offline recipient sees them when their
  add-on next connects. Incoming notifications use the system tray when the
  platform provides it, plus the Tools menu unread count.
- Foreground chat refreshes about every second. The hidden window checks
  less often. Images/GIFs already displayed are kept in place during polling.
- This is a desktop add-on, not an AnkiMobile extension. There is no mobile
  companion website or phone push-notification service in this release.

## Send decks

- Use **Share decks** inside a conversation, or from the empty chat screen.
- Select one or more friends and decks. Selecting a normal parent includes its
  descendants, including nested filtered decks. Expand/collapse the tree to
  choose smaller branches. The optional Anki search further limits selection.
- **My deck setup** defaults ON. It includes dedicated preset copies, preset
  assignments, native per-deck overrides, new/review limits, desired retention,
  learning steps, ordering, and applicable filtered-deck options.
- **My learning progress** defaults OFF. New received cards start New; existing
  receiver cards retain their learning progress unless the receiver explicitly
  selects copied progress or Reset received cards.
- Progress/settings are independent. Source presets and learning state are not
  modified by preparing or sending a transfer.
- Only selected card rows are transferred. Their associated notes, note types,
  note fields and required media are included. A selected cloze still contains
  the original complete note text; unselected sibling card rows are excluded.

## Receive decks and later updates

- The Decks tab and conversation show pending invitations. **View invitation**
  downloads/checks the package and shows actual new/existing cards, updated
  notes and local edit conflicts before importing anything.
- Pick a destination folder. Its value is remembered for this sender/source.
  The original hierarchy is preserved below it, for example:
  `From Jay::Practice::Science::Round 1`.
- New sets offer the sender's setup by default when included. Later updates
  keep receiver settings by default. Applied presets are private copies; the
  receiver's unrelated Default preset is not overwritten.
- Desired retention and preset assignment are copied; an FSRS setup also needs
  FSRS enabled. The invitation has a separate explicit checkbox if enabling
  this Anki-wide setting is necessary. It never silently enables it.
- Identical note GUID/card ordinal pairs are reused. A 60-card set updated to
  80 imports 20 new cards, not another copy of the original 60. Same-second text
  edits are handled too. Deleted/recreated notes have different identities and
  are not automatically merged just because their visible text looks similar.
- Receiver edits are shown side by side and kept by default. Choosing the
  replace-local-edits option explicitly applies the sender's versions.
- Accept downloads/imports directly into desktop Anki. An Anki backup is made
  before collection changes. Decline imports nothing.
- A completed local receipt prevents a second import/reset if the connection
  drops while acknowledging acceptance. Its server receipt retries on reconnect.

## Filtered decks

- Empty normal parents may contain filtered leaf decks. A filtered deck cannot
  be a parent. The hierarchy, exact selected card identities and filter options
  travel together.
- Only the selected cards are required, not the sender's whole home decks.
  Necessary regular home decks are created for those cards on the receiver.
- Sender rules are resolved to receiver card IDs. A sender `is:due` rule never
  accidentally selects an entirely different receiver set. Two-rule filtered
  decks retain their captured membership groups and configured ordering.
- Rescheduling OFF is preserved when applying the sender's setup. Without
  copied settings, a new filtered deck defaults to rescheduling OFF; an existing
  receiver filtered deck keeps its own options.
- **Build the filtered practice decks** can be unchecked to deliver definitions
  and card content without restarting a current practice round.
- Native Anki permits a card in one filtered deck at a time. Overlapping versions
  can all be delivered, but some may initially be empty; empty/rebuild the chosen
  version in Anki when switching between them. Suspended/buried cards are subject
  to Anki's usual filtered-deck eligibility rules.
- Rebuilding a preview round is different from resetting normal learning
  history. New-cards-per-day and FSRS targets do not limit rescheduling-OFF
  preview queues.

## Reset and compatibility details

- Reset received cards uses Anki's native Set as New/Forget operation with
  counts reset. Only cards in that transfer are selected. It does not erase
  historical review-log entries from Anki's statistics.
- Imports use Anki's native package importer, including note types/templates.
  Incompatible field-layout changes are rejected before import, rather than
  silently dropping fields. Resolve such a note type in Anki first.
- Native settings a receiver version cannot represent require updating Anki or
  opting to keep receiver settings. New per-deck retention overrides are kept
  through the native protobuf deck API, not a partial legacy JSON copy.
- The add-on does not provide reviewer hooks, grade cards, create review
  queues, intercept rating shortcuts, or run automatic rescheduling. Explicit
  receiver imports/resets/filter builds are the only collection changes.

## Verification

The test suite uses real Rust-backed Anki collections, an actual local HTTP
relay and two Qt WebEngine interfaces with the actual add-on controller. It
covers accounts, friendship, private image access, emoji, built-in/custom
stickers, group chat, invitation acceptance/rejection, copied presets, fresh
learning, progress preservation/copy/reset, conflicts, filtered hierarchies,
60-to-80 updates and exact cloze-card selection. The GUI test includes real
keyboard input and verifies polling keeps image nodes alive.

See VALIDATION.md for exact tested versions and limitations. Native Windows
DPAPI/tray behavior has not been tested in a live Windows Anki session.

The hosted relay stores records and private attachments persistently. Transfers
are limited to 90 MB each on this service; images to 12 MB. The optional standalone
Python/SQLite server defaults to 250 MB transfers. Switching servers does not
migrate accounts or conversations automatically. Files/messages are private by
authentication and access controls, not end-to-end encrypted. The server owner
controls its database and storage.
