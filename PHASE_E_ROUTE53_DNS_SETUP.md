# Phase E — Route 53 DNS setup for the Horizon Sync staging stack

Hand this file to whoever/whatever applies the DNS change. It is idempotent and
does not touch any existing record.

---

## Verified facts (checked 2026-09-29)

| Fact                           | Value                                                                                                                                                           |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Zone                           | `ciphercode.ai` — **hosted in AWS Route 53**                                                                                                                    |
| Nameservers                    | `ns-9.awsdns-01.com`, `ns-938.awsdns-53.net`, `ns-1504.awsdns-60.org`, `ns-1898.awsdns-45.co.uk`                                                                |
| SOA                            | `ns-1504.awsdns-60.org. awsdns-hostmaster.amazon.com.`                                                                                                          |
| Wildcard                       | **YES** — any unlisted subdomain (random probes were tested) resolves to `3.6.154.21` = `ec2-3-6-154-21.ap-south-1.compute.amazonaws.com` (existing EC2 server) |
| Records for the 4 target names | **none exist explicitly** — they inherit the wildcard                                                                                                           |

**Consequence:** Route 53 answers with the _most specific_ match, so adding explicit
CNAMEs for these 4 names overrides the wildcard. **Do NOT delete or modify the wildcard
record** — other subdomains presumably depend on it.

---

## Records to create

All four are **CNAME**, TTL **300**, zone `ciphercode.ai`.

| Record name                  | Type  | Value (must include trailing dot in Route 53) |
| ---------------------------- | ----- | --------------------------------------------- |
| `horizon.ciphercode.ai`      | CNAME | `ytn9in59.up.railway.app.`                    |
| `stage-admin.ciphercode.ai`  | CNAME | `w3o0989o.up.railway.app.`                    |
| `core-api.ciphercode.ai`     | CNAME | `smgzukh2.up.railway.app.`                    |
| `identity-api.ciphercode.ai` | CNAME | `ogrr04jh.up.railway.app.`                    |

> ⚠️ Each target is **unique per hostname**. Do not point all four at the same value.
> These values are issued by Railway for these specific domains; do not invent them.

---

## Step 0 — credentials

```bash
aws sts get-caller-identity
```

Requires permission for `route53:ListHostedZonesByName`, `route53:ListResourceRecordSets`,
`route53:ChangeResourceRecordSets`, `route53:GetChange`, `route53:GetHostedZone`.

---

## Step 1 — find the hosted zone id and confirm it is the authoritative zone

```bash
ZONE="$(aws route53 list-hosted-zones-by-name --dns-name ciphercode.ai. \
  --query 'HostedZones[0].Id' --output text)"
echo "$ZONE"        # -> /hostedzone/ZXXXXXXXXXXXX

# Sanity check: must print the four awsdns nameservers listed above
aws route53 get-hosted-zone --id "$ZONE" --query 'DelegationSet.NameServers' --output text
```

If the nameservers do not match, **stop** — you are looking at the wrong zone.

---

## Step 2 — pre-flight: confirm nothing conflicts

```bash
aws route53 list-resource-record-sets --hosted-zone-id "$ZONE" --output json > /tmp/r53.json

python3 - <<'PY'
import json
d = json.load(open('/tmp/r53.json'))
want = {
    'horizon.ciphercode.ai.', 'stage-admin.ciphercode.ai.',
    'core-api.ciphercode.ai.', 'identity-api.ciphercode.ai.',
    '*.ciphercode.ai.',
}
for r in d['ResourceRecordSets']:
    if r['Name'] in want:
        vals = [x['Value'] for x in r.get('ResourceRecords', [])] or [str(r.get('AliasTarget', ''))]
        print(f"{r['Name']:34} {r['Type']:6} TTL={r.get('TTL')} {vals}")
PY
```

**Expected:** only `*.ciphercode.ai.` appears. The four target names should be absent.

- If a target name **already exists** as a CNAME with the correct value → skip it.
- If a target name exists as **any other type** (A, AAAA, alias…) → it must be DELETED
  first: Route 53 forbids a CNAME coexisting with any other record at the same name.
  Use `"Action": "DELETE"` with the exact existing record in a batch, then run Step 3.

---

## Step 3 — create all four in a single change batch

Write `/tmp/railway-cnames.json`:

```json
{
  "Comment": "Railway staging: horizon/stage-admin/core-api/identity-api for Horizon Sync BW-staging",
  "Changes": [
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "horizon.ciphercode.ai",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{ "Value": "ytn9in59.up.railway.app" }]
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "stage-admin.ciphercode.ai",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{ "Value": "w3o0989o.up.railway.app" }]
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "core-api.ciphercode.ai",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{ "Value": "smgzukh2.up.railway.app" }]
      }
    },
    {
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "identity-api.ciphercode.ai",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [{ "Value": "ogrr04jh.up.railway.app" }]
      }
    }
  ]
}
```

Apply and wait for the change to propagate:

```bash
CHANGE="$(aws route53 change-resource-record-sets --hosted-zone-id "$ZONE" \
  --change-batch file:///tmp/railway-cnames.json \
  --query 'ChangeInfo.Id' --output text)"
echo "$CHANGE"

aws route53 wait resource-record-sets-changed --id "$CHANGE"
echo "INSYNC"
```

`UPSERT` makes this safe to re-run.

---

## Step 4 — verify resolution

```bash
for H in horizon stage-admin core-api identity-api; do
  printf '%-24s ' "$H.ciphercode.ai"
  dig +short CNAME "$H.ciphercode.ai" @8.8.8.8 | tr '\n' ' '
  echo
done
```

Expected (TTL is 300, allow up to ~5 minutes):

```
horizon.ciphercode.ai      ytn9in59.up.railway.app.
stage-admin.ciphercode.ai  w3o0989o.up.railway.app.
core-api.ciphercode.ai     smgzukh2.up.railway.app.
identity-api.ciphercode.ai ogrr04jh.up.railway.app.
```

Note: `dig +short CNAME` returning the Railway target is the correct result. A leftover
`3.6.154.21` answer means the wildcard is still winning — re-check Step 2/3.

---

## Step 5 — Railway issues TLS automatically

No action needed; Railway detects the records and provisions certificates (usually
1–10 minutes). Check with:

```bash
railway domain status horizon.ciphercode.ai -s horizon-ui -e staging \
  --project fd8e8c06-a0a1-4592-9d6e-9a63c6cfb090
# repeat for stage-admin.ciphercode.ai (same service),
#   core-api.ciphercode.ai  -> core-service
#   identity-api.ciphercode.ai -> identity-service
```

Then confirm the hosts actually serve:

```bash
curl -sI https://horizon.ciphercode.ai/healthz      # 200
curl -sI https://stage-admin.ciphercode.ai/healthz  # 200
curl -sI https://core-api.ciphercode.ai/health      # 200
curl -sI https://identity-api.ciphercode.ai/health  # 200
```

---

## Things NOT to do

1. **Do not create an Alias (A) record.** Route 53 Alias records can only target AWS
   resources (ELB, CloudFront, S3, …). `*.up.railway.app` is not one, so it must be a
   plain **CNAME**.
2. **Do not delete or edit `*.ciphercode.ai`** (or any other existing record).
3. **Do not add A/AAAA records** for these four names.
4. **Do not reuse one CNAME value for all four** — each is hostname-specific.
5. Do not omit the trailing dot mis-match: Route 53 stores values like
   `ytn9in59.up.railway.app.` (the console/CLI adds it).
