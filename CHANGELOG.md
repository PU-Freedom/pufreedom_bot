# Changelog

All notable changes to this project will be documented in this file.

## [v0.0.01] - 2026-03-31

### Features

- **Dynamic content handling** (#13): Refactored message handling to support all Telegram content types - audio, video notes, locations, venues, and other custom types - via a dynamic handler config instead of hardcoded type checks.

- **Alias system** (#15): Users can now set a unique alias displayed as the author placeholder on channel posts.
  - Added `alias` field to the User model with repository CRUD logic (#17).
  - Alias creation and management exposed via a `/settings` keyboard flow (#18).
  - Alias is tied to subscription: created only while subscribed, lost on unsubscribe.

- **Anon comments** (#19): New `anon/` command for leaving anonymous comments on channel posts.
  - Supports comments under channel posts (#20) and replies to existing comments (#21).
  - Reply notifications sent to the original commenter (#30).

- **Subscription guard** (#14): Decorator-based guard that requires users to be subscribed before sending messages or using bot features.

- **Quick commands** (#43): Registered bot command menu with the following commands:
  - `start/` - init the bot
  - `settings/` - manage user settings (for now only alias)
  - `anon/` - leave an anonymous comment on a channel post

### Bug Fixes

- **Media groups** (#12): Resolved race conditions that caused out-of-order delivery and lost captions in multi-photo/video groups.
- **Reply logic** (#27): Refined reply handling for media group messages.
- **Link cleaning** (#28): Fixed formatting issues where links were not cleaned correctly.
- **Text formatting** (#29): Fixed text formatting preservation across forwarded and processed messages.

