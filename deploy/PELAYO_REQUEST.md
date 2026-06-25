# Infrastructure request for Pelayo

Copy-paste template for AWS / DNS changes needed before HTTPS cutover.

---

**Subject:** Sybol Compliance Engine — Elastic IP, security group, DNS

Hi Pelayo,

We need a few AWS changes for the public demo at EC2 instance **54.154.92.29** (user `javier`, repo `sybol-compliance-engine`):

1. **Elastic IP** — attach an Elastic IP to this instance so the public address survives stop/reboot.

2. **Security group** — allow inbound:
   - TCP **443** (HTTPS via Caddy)
   - Keep TCP **8000** open during transition (direct API access for debugging)

3. **DNS** — create or confirm:
   - `compliance.sybol.id` → Elastic IP (A record)

Once the Elastic IP and DNS are live, we will:
- Install Caddy with [`deploy/Caddyfile`](Caddyfile)
- Set `PUBLIC_BASE_URL=https://compliance.sybol.id` in `src/.env`
- Enable systemd service [`deploy/sybol-api.service`](sybol-api.service) (needs sudo on the box)

Optional (medium term): IAM instance role with `ssm:GetParametersByPath` on `/sybol/compliance/*` for secrets — see [`deploy/README.md`](README.md) SSM section.

Thanks!

---

**Instance:** 54.154.92.29  
**SSH:** `ssh -i ~/.ssh/sybol_ie_javier javier@54.154.92.29`  
**Current demo URL:** http://54.154.92.29:8000/
