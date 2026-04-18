---
tags: [hermes, client]
---

# clients/ — Per-Client Deployment Overlays

> Each client deployment gets its own subdirectory with a config overlay.
> The base `.env.template` in the repo root covers all possible variables.
> Each `clients/<name>/.env.client.template` overrides only what is client-specific.

## How Deployments Work

Hermes is a single-tenant product. One running process per client. Each process
reads a `.env` file that is built by merging the base template with the client overlay:

```
.env.template (base — all keys, no values)
    + clients/<name>/.env.client.template (client-specific values)
    → .env (never committed — lives only on the client's machine)
```

The `.env` file on the client's machine is the only file with real credentials.
Nothing in this directory ever contains real credentials.

## Onboarding a New Client

1. Create `clients/<client-name>/` (use lowercase, no spaces)
2. Copy `clients/_template/README.md.template` → `clients/<client-name>/README.md`
   Fill in client business context, POS type, email provider, expected PO volume.
3. Copy `clients/_template/.env.client.template` → `clients/<client-name>/.env.client.template`
   Fill in the TODO placeholders with real key names (not values).
4. On the client's machine: build their `.env` by combining base + overlay, then add values.
5. Test with `A2000_MODE=mock` before pointing at the live POS.
6. Once mock tests pass, move to the appropriate live mode (`edi` or `api`).

## Directory Structure

```
clients/
├── README.md                        (this file)
├── _template/                       (scaffold for new clients)
│   ├── README.md.template
│   └── .env.client.template
└── lowinger/                        (Emmanuel Lowinger — first deployment)
    ├── README.md
    └── .env.client.template
```

## What Does NOT Go Here

- Real credentials or API keys (use the `.env` on the client machine)
- Client data, PO files, or invoices (those live in the deployment's `logs/` and `storage/`)
- Client-specific code changes (all clients run the same codebase)

## Obsidian Links
- [[brain/HERMES]] | [[clients/lowinger/README]]
