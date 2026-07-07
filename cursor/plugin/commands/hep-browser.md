Update fallback: 자동 업데이트가 안 되면 `hephaestus update`를 한 번 실행하세요. 업데이트하지 않아도 현재 버전 명령은 그대로 동작합니다.

# Hephaestus Browser

Use this for browser-required work: rendered pages, JS-heavy sites, click/form
flows, or login-visible evidence. Prefer the Agentlas browser hardpoint first.

With a URL plus an explicit instruction, `hep-browser` runs browser automation
through `browser.agent_cli` before taking the final snapshot. Use `--read` to
force snapshot-only mode.

Resolve the runner (`~/.agentlas/runtime/current/bin/hephaestus`, then
`./bin/hephaestus`) and run:

`"$RUNNER" hep-browser "<url-or-query>"`

Report whether `browser.agent_cli` mounted, whether setup is needed, and the
receipt id. For automation, also report the action and final snapshot status.
If setup is needed, show `hep-browser --setup` and `hep-browser --check`.
