# FC deployment

Target URL:

`https://fc.quietwire.ai/playable/`

The existing nginx configuration already serves static files under the CAP frontend root, so v0 needs **no nginx configuration change and no reload**.

The install script:
- requires root;
- refuses an unmarked pre-existing `/playable` target;
- backs up a previous Playable Universe deployment;
- copies only the staged static site;
- leaves CAP core/gateway/nginx configuration untouched;
- performs a public HTTPS smoke test.

Activation command:

```bash
sudo bash /var/tmp/playable-universe-stage/deploy/install-fc.sh
```