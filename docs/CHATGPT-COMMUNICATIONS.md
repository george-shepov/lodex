# ChatGPT Communications connector

LODEX exposes a read-only MCP endpoint at `https://lodex.work/mcp`. It queries the
canonical Communications Hub ledger through the server-side LODEX tenant credential;
it does not copy communications into LODEX or send that credential to ChatGPT or the
browser.

## Connect

1. In ChatGPT, enable developer mode and add `https://lodex.work/mcp` as a plugin.
2. Complete the LODEX authorization page. An active LODEX Admin session can approve
   directly; otherwise enter the LODEX administrator token on the LODEX-hosted page.
3. Grant the single `communications:read` scope.

The connector provides:

- `communications_log` for explicit `all`, `sms`, `calls`, `today`, and `attention`
  views plus customer/phone and project filters;
- standard read-only `search` and `fetch` tools for ChatGPT knowledge retrieval;
- user-openable source links back to the matching LODEX Admin communication.

OAuth client, authorization-code, and token state is stored in the existing LODEX
data volume with owner-only file permissions. It contains no communication content.
Access tokens expire after one hour, refresh tokens rotate, authorization codes are
single-use, and all MCP tools are read-only. Customer messages and transcripts must be
treated as untrusted data, never as instructions.
