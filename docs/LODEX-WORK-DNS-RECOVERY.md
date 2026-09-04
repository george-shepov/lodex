# lodex.work DNS recovery baseline

Captured from the Namecheap BasicDNS record table on 2026-09-04 before completing the Cloudflare migration.

This file contains public DNS data only. Never commit mail-server credentials, API tokens, Cloudflare tokens, or DKIM private keys.

## Nameservers

- Namecheap BasicDNS rollback:
  - `dns1.registrar-servers.com`
  - `dns2.registrar-servers.com`
- Cloudflare target:
  - `ethan.ns.cloudflare.com`
  - `ruth.ns.cloudflare.com`

## Recovered records

| Type | Host | Value | TTL | Cloudflare proxy |
| --- | --- | --- | --- | --- |
| A | `@` | `104.237.11.29` | Automatic | DNS only during validation; then Proxied |
| A | `mail` | `104.237.11.29` | Automatic | DNS only |
| CNAME | `www` | `lodex.work.` | Automatic | DNS only during validation; then Proxied |
| TXT | `@` | `v=spf1 mx -all` | Automatic | Not applicable |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@lodex.work` | Automatic | Not applicable |
| TXT | `v1-ed25519-20260827._domainkey` | `v=DKIM1; k=ed25519; h=sha256; p=utTC62qfGljDtYVZygSfaSEf2TulcK9Kmsyu8dXz6cg=` | Automatic | Not applicable |
| TXT | `v1-rsa-20260827._domainkey` | `v=DKIM1; k=rsa; h=sha256; p=MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA98bzrLtKSZNcJr5cbCIx3fxG8vL8sQx05r79KxcreqpRCU885uev/uxzQ8vVHIua51RUg+KMESiNSc/efS4eb5BQsAIYACPdgUa3vbtF9IbOtAw4NspRtV65KRaqfbpeJiZvfGVXAtT1AmEVSDfE9Q2f6BqbVpvQ/2e7C5c+Uz5PIX24/Yec1kOhryb5ttTR9o1ES5OgbTwfW41MS2Z5CrlQenDd8XYcRj94OBzPh+Mcw36tX+kBN7apk7DQjIxVtfzAs0HaP5awT23+wZm4Ak0bKQI1QNlM7vVqMfWDaOXWMayslxD49jRE2WelK5STZaMLj6EqPGWHUv2Z4+CqowIDAQAB` | Automatic | Not applicable |

The RSA public key above is a continuous 392-character Base64 value. Do not introduce spaces when copying it into a DNS provider.

## Records still requiring confirmation

- **MX:** No MX record appeared in the recovered Namecheap table. Do not invent one. Confirm the intended mail provider and destination before migration. The recovered SPF policy uses the `mx` mechanism, so mail authorization depends on a correct MX configuration.
- **Google Search Console:** No `google-site-verification` TXT record appeared in the recovered table. Retrieve the exact token from Search Console and add it to the authoritative DNS zone.
- **Other services:** Check for provider-verification, CAA, SRV, and any non-web subdomain records before changing nameservers again.

## Safe Cloudflare migration

1. Keep Namecheap BasicDNS authoritative while reconstructing the Cloudflare zone.
2. Add every confirmed record to Cloudflare before changing nameservers.
3. Keep `mail` and all mail-related records DNS only. Only HTTP/HTTPS web hostnames should be proxied.
4. Initially keep `@` and `www` DNS only and verify DNS, HTTP, HTTPS, redirects, `robots.txt`, `sitemap.xml`, API health, and the customer/admin flows.
5. Set Cloudflare SSL/TLS encryption mode to **Full (strict)**. Do not use Flexible mode because the origin enforces HTTPS.
6. Enable the Cloudflare proxy for `@` and `www`, then repeat the production checks.
7. Confirm mail sending, DKIM signing, SPF evaluation, DMARC reporting, and inbound delivery before declaring the migration complete.
8. Only after the Cloudflare zone is verified should Namecheap be changed to `ethan.ns.cloudflare.com` and `ruth.ns.cloudflare.com`.

## Recovery rule

If the Cloudflare zone is incomplete or the cutover breaks production, switch the registrar back to Namecheap BasicDNS and validate that the records in this document still match the active Namecheap zone.
