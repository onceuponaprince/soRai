# Panel Scaffold

Browser-based scaffold for operator/admin flows against the current local API.

## Run

1. Start API server (CLI or Django scaffold).
2. Serve this folder statically:

```bash
cd panel
python3 -m http.server 8787
```

3. Open `http://127.0.0.1:8787`.

## Flows Included

- Health and role introspection (`whoami`)
- Profile listing
- Profile metadata summary (`summary`, `necessary`, `sink`)
- Signup request
- Pending signup admin approve/reject
- Run creation
- Approval decision actions
- Admin API-key list/revoke/reactivate
