# FC deployment

Target URL:

`https://fc.quietwire.ai/playable/`

The existing nginx configuration already serves static files under the CAP frontend root, so v0 needs **no nginx configuration change and no reload**.

The install script:
- resolves the repository root from its own location;
- requires root;
- refuses an unmarked pre-existing `/playable` target;
- backs up a previous Playable Universe deployment;
- copies only the repository's `site/` tree;
- leaves CAP core/gateway/nginx configuration untouched;
- performs a public HTTPS smoke test.

From a checked-out copy of this repository on FC:

```bash
sudo bash deploy/install-fc.sh
```

The original bootstrap used a Quiet Hands private `/var/tmp` namespace. That transient staging path is **not** a host-shell deployment interface; the repository is now the durable source of truth for deployment.
