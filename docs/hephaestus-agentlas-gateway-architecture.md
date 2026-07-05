# Hephaestus and Agentlas Gateway Architecture

This document defines the messaging-gateway pattern Hephaestus and Agentlas
should share, using Hermes Agent and OpenClaw as reference implementations.

The short version: a gateway is not the bot account itself. It is the control
plane behind the bot. It turns Telegram, Slack, Discord, WhatsApp, email, SMS,
and similar messages into normalized inbound events; checks who sent them;
maps the channel, account, and conversation to the right agent; keeps the
session boundary; streams progress; asks for approval when needed; and writes a
delivery receipt before the UI says the message was delivered.

## Research Sources

Primary sources inspected:

- Hermes Agent docs: Messaging Gateway, Telegram, Slack.
- Hermes Agent source: `gateway/platforms/base.py`,
  `gateway/platform_registry.py`, `gateway/pairing.py`,
  `gateway/slash_access.py`, `plugins/platforms/telegram/adapter.py`, and
  `plugins/platforms/slack/adapter.py`.
- OpenClaw docs: Gateway configuration, Telegram, Slack, and multi-agent
  routing.
- OpenClaw source: `src/channels/message/types.ts`,
  `src/channels/message/contracts.ts`,
  `src/channels/plugins/configured-binding-compiler.ts`,
  `src/channels/plugins/configured-binding-match.ts`,
  `src/channels/message-access/runtime.ts`, and
  `src/channels/command-gating.ts`.

## What To Copy

| Pattern | Hermes | OpenClaw | Agentlas/Hephaestus interpretation |
|---|---|---|---|
| Single gateway process | One background process owns all messaging platforms, sessions, cron, and delivery | One Gateway owns channels, config, Control UI, mobile nodes, and routing | One Agentlas Gateway process per user/workspace, local by default and optionally relay/hosted |
| Platform adapter contract | `BasePlatformAdapter` normalizes message events, send, typing, media, progress, approvals | Channel message adapter declares send/receive/durable receipt capabilities | `GatewayChannelAdapter` should expose receive, send, media, receipt, typing/progress, approval, and lifecycle hooks |
| Plugin/channel registry | `PlatformRegistry` lazily loads platform plugins and env/YAML bridges | Channel plugin registry, schemas, catalog, config writes, proof contracts | Hephaestus packages should ship channel manifests; Agentlas Web/Desktop should list/install/configure them |
| Sender authorization | allowlists, pairing store, admin/user slash access | `dmPolicy`, `groupPolicy`, access graph, access groups, command gates | Default deny unknown senders; pairing or allowlist; command tiers; no raw IDs in public packages |
| Binding and routing | Per-chat sessions with platform/session source | `bindings` map channel/account/peer to `agentId` and session target | Bind `channel + accountId + peer` to `agentBindingId` or local agent id |
| Group activation | mention gates, silence tokens, slash commands | mention patterns, room events, visible reply modes | Group rooms should default quiet; visible replies require mention or explicit send tool |
| Durable delivery | SendResult, media delivery helpers, processing start/complete hooks | receipts, durable final capabilities, live preview finalizers | Every outbound message should produce a receipt record before claiming delivery |
| Background work | `/background`, cron, final result delivery | background process and channel notification controls | Agentlas automations and Hephaestus Stormbreaker runs should deliver result/error summaries to the origin channel |

## Target System

```text
Telegram / Slack / Discord / WhatsApp / Email / SMS
  -> GatewayChannelAdapter
  -> Ingress Kernel
       - platform identity normalization
       - DM/group policy
       - pairing / allowlist / access group check
       - mention and command gate
  -> Binding Resolver
       - channel + accountId + peer/thread/topic
       - maps to Agentlas agent binding or local Hephaestus agent
  -> Session Store
       - per chat/thread/agent session
       - reset and background task rules
  -> Agent Runtime
       - Hephaestus route/call/search/build/upload
       - Agentlas Web runtime bundle and invocation
       - Agentlas Desktop local run graph
  -> Delivery Kernel
       - progress update
       - approval prompt
       - result/error summary
       - receipt ledger
  -> GatewayChannelAdapter.send()
```

## Contract File

Hephaestus now has a value-free gateway contract:

```text
schemas/gateway-channel.schema.json
```

It intentionally stores credential references, not raw tokens:

```json
{
  "schemaVersion": "agentlas.gateway-channel.v1",
  "gatewayId": "mason-local",
  "channels": {
    "telegram": {
      "provider": "telegram",
      "enabled": true,
      "mode": "long_polling",
      "accounts": {
        "default": {
          "credentials": {
            "botToken": {
              "source": "env",
              "id": "TELEGRAM_BOT_TOKEN"
            }
          },
          "access": {
            "dmPolicy": "pairing",
            "groupPolicy": "allowlist"
          }
        }
      }
    }
  },
  "bindings": [
    {
      "agentId": "agentlas-core-engine-meta-agent",
      "match": {
        "channel": "telegram",
        "accountId": "default",
        "peer": {
          "kind": "direct",
          "id": "telegram-user-id"
        }
      }
    }
  ]
}
```

## Gateway Modes

Agentlas should support three deployment shapes:

| Mode | Use case | Network shape | Borrowed pattern |
|---|---|---|---|
| Local gateway | Desktop/Terminal user wants private chat control | Local process, outbound API calls only | Hermes macOS launchd and OpenClaw local Gateway |
| Relay gateway | Slack or mobile ingress is handled by a trusted router | Authenticated websocket relay to the user's gateway | OpenClaw Slack relay mode |
| Hosted gateway | Cloud workspace wants always-on delivery | Agentlas Cloud hosts ingress and routes to workspace agents | Hermes VPS/serverless gateway plus OpenClaw HTTP Request URLs |

Slack should support both Socket Mode and HTTP Request URLs. Telegram should
start with long polling for local setups and add webhook mode for hosted or
relay deployments.

## Channel Adapter Interface

Every adapter should implement this logical interface, even if the runtime
language differs:

```text
start()
stop()
receive(raw_event) -> GatewayInboundEvent
send(GatewayOutboundMessage) -> GatewayDeliveryReceipt
sendTyping(chat_id)
sendProgress(chat_id, progress)
sendApproval(chat_id, approval_request)
sendMedia(chat_id, media)
health()
```

Required normalized fields:

```text
channel
accountId
chatId / peerId
threadId / topicId
sender stable id
sender display label
message id
message text
attachments
command facts
mention facts
raw event pointer
```

Raw platform payloads can be kept in a short-lived debug buffer, but durable
ledgers should store redacted metadata and receipts, not whole private chats.

## Access Rules

Safe default:

```text
unknown sender -> pairing code or deny
DM -> pairing or explicit allowlist
group/channel -> require configured group + sender allowlist + mention
dangerous command -> owner/admin approval
background task -> result/error delivery only by default
```

Patterns to copy:

- Hermes pairing: cryptographically random short code, one-hour expiry,
  rate limit, failed-approval lockout, file permissions.
- OpenClaw access graph: resolve sender, route, command, group, pairing, and
  mention facts before dispatch.
- Hermes slash access: allowed sender is not automatically admin. Admin and
  regular user command sets are separate.
- OpenClaw command gating: text control commands should be blocked unless a
  configured authorizer permits them.

## Binding Rules

Bindings are the bridge from chat identity to agent identity:

```text
channel + accountId + peer.kind + peer.id + optional parent/thread
  -> agentId / agentBindingId
  -> sessionKey
```

This lets one gateway serve:

- one Telegram bot per agent;
- one Slack app with channels bound to different agents;
- one WhatsApp number split by sender;
- one group where mentions route to a specific agent;
- multiple users sharing a gateway without memory/session cross-talk.

Agentlas Web should store bindings against `agentBindingId`. Hephaestus local
mode can store local `agentId` or package slug. Agentlas Desktop should render
the same binding table and pairing queue in UI.

## Delivery Rules

Do not treat a send as successful just because the agent produced text. Delivery
is complete only after the adapter returns a receipt:

```text
logical send id
platform message ids
thread/reply ids
sent timestamp
edit/delete token when available
raw result pointer
delivery status
```

Progress should default to quiet summaries:

- accumulate tool progress in one editable message where supported;
- send final result/error for background tasks;
- allow `[SILENT]`, `SILENT`, `NO_REPLY`, and `NO REPLY` as exact final-output
  delivery suppression tokens;
- never hide failures via silence tokens.

## Connection UX

The product surface should make connection feel like one guided job, not a
settings page full of provider terms. The user goal is:

```text
Connect this agent to Telegram, send one test message, and know the delivery is real.
```

Recommended setup flow:

1. Pick an agent first. The user should not start with tokens or provider
   acronyms.
2. Pick a channel with plain labels. Telegram is the first supported channel;
   Slack, Discord, WhatsApp, email, and SMS use the same contract later.
3. Show the recommended connection mode for the user's surface: Telegram long
   polling for local, Slack Socket Mode for local, webhook/relay for hosted.
4. Ask for a credential reference, not a raw secret in the package. The UI can
   help create `TELEGRAM_BOT_TOKEN` or `SLACK_BOT_TOKEN` locally, but the saved
   contract stays value-free.
5. Let the user choose the conversation or paste the channel/user id. For group
   rooms, show that mention gating is on by default.
6. Generate or approve the pairing code. Make it obvious that DM pairing is not
   admin access and does not authorize group rooms.
7. Send a test message and wait for a delivery receipt. Setup is still pending
   until the platform confirms the send.
8. Finish with a compact status card: connected account, bound agent, allowed
   conversation, policy, last receipt, and next action.

Failure UX should be specific and recoverable:

- Missing token: show the exact credential reference name and where to save it.
- Unauthorized sender: offer approve pairing, add allowlist, or keep denied.
- Group not responding: explain whether mention is missing, room is not
  allowlisted, or sender is not approved.
- Agent responded but no receipt: mark delivery as uncertain and offer retry.
- Provider app missing scope: show the missing Slack/Telegram capability in the
  checklist instead of exposing raw API errors first.

The screen model should be a left-to-right or top-to-bottom checklist, not a
freeform settings table. Advanced JSON should remain available, but should be
secondary to the guided connection path.

## Product Mapping

### Hephaestus Core

Add the gateway contract to generated packages:

- `.agentlas/gateway-channel.json` for local/private installs.
- `schemas/gateway-channel.schema.json` for package validation.
- `templates/gateway-channel.json.tpl` for packages that request Telegram,
  Slack, Discord, WhatsApp, email, SMS, or similar channels.
- `docs/gateway-channel.md` when a package asks for Telegram, Slack, Discord,
  WhatsApp, email, SMS, or similar channel access.
- `scripts/verify-gateway-channel-contract.sh` to block raw tokens, invalid
  policies, missing bindings, and open public bots with broad tool access.

New Hephaestus commands should be staged as:

```text
hephaestus gateway status
hephaestus gateway setup telegram
hephaestus gateway setup slack
hephaestus gateway pairing list
hephaestus gateway pairing approve <channel> <code>
hephaestus gateway run
```

### Agentlas Web

Agentlas Web should own the cloud/workspace surfaces:

- channel connector catalog;
- OAuth/setup wizard where the provider supports it;
- value-free credential reference map;
- hosted/relay/local mode selection;
- workspace `agentBindingId` bindings;
- pairing approval queue;
- delivery receipt and failure ledger;
- public package republish boundary when a gateway-capable agent is uploaded.

### Agentlas Desktop

Agentlas Desktop should own the local operator surface:

- local gateway process supervisor;
- Telegram/Slack setup screens;
- pairing codes and approval actions;
- channel status probes;
- message receipt and failure timeline;
- “send result to channel” target picker for automations and run graphs.

## Implementation Order

1. Schema and docs: ship the value-free channel contract and product mapping.
2. Core gateway kernel: shared inbound event, outbound receipt, access decision,
   and binding resolver types.
3. Telegram local adapter: BotFather token, long polling, DM pairing,
   allowlist, group mention gating, text/files/images.
4. Slack local adapter: Socket Mode, bot/app token refs, app mentions, DMs,
   threads, slash command gate, file read/write scopes.
5. Agentlas Web relay: signed HTTP/websocket relay mode with workspace-bound
   destination routing.
6. Desktop UI: gateway setup, pairing inbox, channel health, and receipts.
7. Package verification: block raw credentials and unsafe `open` policies in
   public artifacts.

## Non-Negotiables

- No raw Slack/Telegram tokens in public packages, Hub metadata, or memory.
- `open` sender policy is invalid for agents with terminal, browser, file, or
  package mutation access unless tool access is separately sandboxed.
- Group messages are quiet by default and require mention or an explicit
  message-send tool.
- Pairing grants DM access only. It does not grant group, admin, or dangerous
  command authority.
- Every outbound send needs a receipt; every failed send needs a failure event.
- Gateway configs must survive restart and should keep a last-known-good copy.
- Adapters must declare capabilities; core must not assume files, voice,
  threads, streaming edits, or reactions exist.

## Open Questions

- Whether Agentlas Cloud should host provider webhooks directly or require a
  user-owned relay for early releases.
- Whether Telegram/Slack adapters should live in Hephaestus public core or as
  installable Agentlas channel plugins.
- Whether group/channel history should ever be indexed into ontology memory by
  default. The safe answer for now is no: use explicit import or user-approved
  source registration.
