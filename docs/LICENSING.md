# Licensing — how it works and its limits

## For the vendor (you)
1. **Once:** `python tools/license_tool.py keygen --out ./vendor_keys` on YOUR computer. Back up `vendor_private.pem` safely
   (if lost you cannot issue/renew licences; if leaked anyone can). Copy `vendor_public.pem` to `core/keys/vendor_public.pem`
   in the master and build releases from it.
2. **Per customer:** the customer opens *Licence* in the app and sends you the *activation request code*. You run:
   `python tools/license_tool.py issue --private ./vendor_keys/vendor_private.pem --request <code> --company "ACME" --days 365 --max-users 50`
   and send back the produced file. The customer pastes it into the app.
3. **Renew:** issue a new licence the same way. **Revoke:** `license_tool.py revoke ... --serial N --id <license_id> --out revocations.json`
   (serial must increase each time) and send the file, or host it at the URL set in `license_server_url`.

## What is checked on the server (never in the browser)
- Signature (Ed25519) — a changed licence is rejected.
- Deployment ID — derived from the server's machine id + this installation's random id. A licence for another server is rejected.
- Expiry date (+ grace period), user limit, features, revocation list.
- Clock rollback — the last time seen is stored with a keyed MAC; moving the clock back locks the system.
- When not licensed: only Super Administrators can sign in, and only the Licence/Account pages work. All activation events are logged.

## Honest limits
- Someone with full control of the server **and** willing to modify the source code can remove the checks. No software-only scheme prevents this.
  This design stops copying/USB sharing, tampering with the licence file, wrong-server use, clock tricks, and gives you expiry/revocation/audit.
  Combine it with a contract and legal terms. For stronger protection, host the application for the customer yourself.
- Hardware changes require a new licence (new deployment ID).
