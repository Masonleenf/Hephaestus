---
description: Use the Agentlas browser hardpoint for browser-required work.
---
Update fallback: 자동 업데이트가 안 되면 `hephaestus update`를 한 번 실행하세요. 업데이트하지 않아도 현재 버전 명령은 그대로 동작합니다.

# Hephaestus Browser

Raw arguments: `$ARGUMENTS`

```bash
RUNNER=""
for c in "$HOME/.agentlas/runtime/current/bin/hephaestus" ./bin/hephaestus; do
  [ -x "$c" ] && RUNNER="$c" && break
done
[ -n "$RUNNER" ] || { echo "Hephaestus runtime not found. Run the installer first." >&2; exit 1; }
"$RUNNER" hep-browser "$ARGUMENTS"
```

Use this for rendered/browser-required work and report the `browser.agent_cli`
status plus receipt id. With a URL and an explicit instruction, this performs
browser automation before taking the final snapshot:

```text
/hep-browser https://example.com "click the Docs link and report what changed"
/hep-browser https://example.com --act "open pricing" --cdp 9222 --keep-open
/hep-browser https://example.com "extra context only" --read
```

If setup is needed, show `hep-browser --setup` and `hep-browser --check`.
