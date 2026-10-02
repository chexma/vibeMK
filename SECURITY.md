# Security Policy

## Supported Versions

vibeMK is in alpha. Only the latest release gets fixes; there are no
maintenance branches for older ones.

| Version | Supported |
| ------- | --------- |
| 0.5.x   | ✅ |
| < 0.5   | ❌ |

## Reporting a Vulnerability

**Do not open a public issue.**

Use GitHub's private vulnerability reporting:
[**Report a vulnerability**](https://github.com/chexma/vibeMK/security/advisories/new).
The report stays private between you and the maintainer until a fix is
published, and an advisory can be issued directly from it.

Please include what you have: what the flaw allows, how to reproduce it, the
vibeMK and Checkmk versions, and a suggested fix if you have one.

This is a spare-time project. Expect an acknowledgement within a few days
rather than within hours, and no guaranteed fix timeline. If a report sits
unanswered for two weeks, you are free to disclose it publicly.

Reporters are credited in the advisory unless they ask not to be.

## What is in scope

vibeMK holds a Checkmk account and exposes it to a language model. The
interesting failure modes follow from that:

- Anything that lets a caller reach the Checkmk API **without** the
  configured credentials, or with more authority than the automation user has
- Credential exposure — in logs, in error messages, in tool output, or in the
  `tools/list` catalogue
- Authentication bypass on the HTTP transport (`VIBEMK_HTTP_TOKEN`)
- A tool annotated `readOnlyHint` that in fact writes, or one annotated
  non-destructive that in fact destroys. Clients use those annotations to
  decide what to confirm, so a wrong one is a real vulnerability, not a
  documentation bug

## What is not in scope

- **The model deciding to delete something.** vibeMK gives an LLM write
  access to your monitoring system; that is what it is for. Scope the
  automation user's permissions, and set `NEVER_ACTIVATE_CHANGES=true` if you
  want changes staged rather than activated.
- Findings that need `CHECKMK_VERIFY_SSL=false`, which is documented as
  unsafe and defaults to on.
- Vulnerabilities in Checkmk itself — report those to
  [Checkmk](https://checkmk.com/security).

## Running it safely

**Credentials.** vibeMK reads them from the environment. Keep them out of any
file you commit, and give the automation user the narrowest role that does
the job — read-only if you only want analysis. Checkmk's own audit log
records what that user did, which is worth having when an LLM is driving.

**The HTTP transport.** `--transport http` turns a local tool into a network
service that holds your Checkmk account, so whoever reaches the port inherits
it. `VIBEMK_HTTP_TOKEN` is mandatory and is the only thing in the way. vibeMK
binds to `127.0.0.1` unless told otherwise, and it does not terminate TLS —
put a reverse proxy in front of it before exposing it beyond the host.

**Logs.** Debug logging (`LOGFILE`) records endpoints and responses, which
can include host names and comment text. Tool arguments are deliberately not
logged, because they carry secrets for the password tools. Give the log file
restrictive permissions.
