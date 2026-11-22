# Deploying with Docker (port 5222)

## Requirements
- A server (Linux recommended; Windows/macOS with Docker Desktop also works), 2 GB RAM or more, Docker + Docker Compose v2.
- Port **5222** reachable by your users (open it in the server firewall).

## First start
```bash
unzip AssetMaster.zip && cd AssetMaster
docker compose up -d --build
docker compose logs assetmaster | grep "SETUP CODE"      # the one-time setup code
```
Open `http://SERVER-IP:5222`, enter the setup code, create the company and the first administrator.
Then open **Licence**, copy the *activation request code*, send it to the vendor, and paste the licence file you receive.

## Data and backups
Everything is in the Docker volume `am_data` (mounted at `/data` inside the container):
`data.db` (database) · `uploads/` · `backups/` · `secrets.json` (secret key) · `config.json` · `install_id` · `machine_id`.

**Full backups** (`backup_<date>_<time>_<reason>.zip`) contain the database *and* every uploaded file (documents, signed
receipts, logo) plus a checksum list. One is made automatically every day (02:00 local time, see `TZ`), on demand from
the Backups page, or with the CLI. The newest 14 are kept. A database-only copy (`data_*.db`) is also taken right before
every upgrade.

- **Keep a copy off the server** — a backup on the same disk does not survive a disk failure. Super administrators can
  download any backup from the Backups page; or copy the folder:
  `docker compose cp assetmaster:/data/backups ./backups-copy`
- **Verify** a backup at any time (Backups page → Verify, or `manage.py verify <file>`): every file is re-hashed and the
  database integrity-checked.
- **Health:** the Backups page shows a *System health* panel; on the server run `manage.py check` (exit code 1 on a problem,
  suitable for monitoring).

```bash
docker compose exec assetmaster python tools/manage.py backup
docker compose exec assetmaster python tools/manage.py verify backup_20260101_020000_auto.zip
docker compose exec assetmaster python tools/manage.py check
```
Restore (stop the app first; the current state is saved as a `before-restore` backup automatically):
```bash
docker compose stop
docker compose run --rm assetmaster python tools/manage.py restore backup_20260101_020000_auto.zip
docker compose up -d
```
To restore on a **new server**: copy the `.zip` into the new instance's `backups/` folder (or give the full path) and
run the same command. A new server has a new deployment ID, so request a new licence afterwards.

**Restore drill:** do a test restore on a spare machine once in a while — a backup you have never restored is a hope, not a backup.
The automated test `tests/test_phase7.py` performs this drill (backup → damage → restore → compare every row and file).

## Performance
`tests/perf_check.py` seeds 20,000 assets / 5,000 employees / 25,000 assignments and times every page. On a laptop every
screen answers in under 0.5 s; screens show at most 2,000 report rows (totals and Excel exports always include all rows).

## Container hardening
`docker-compose.yml` runs the app as an unprivileged user with a read-only filesystem (only `/data` and a small `/tmp`
are writable), no Linux capabilities, `no-new-privileges`, and a 60-second idle timeout per connection.

## Time zone
Set the company's time zone in `.env` (next to `docker-compose.yml`) so overdue returns, warranty days and the
02:00 daily backup follow local time, e.g. `TZ=Asia/Riyadh` or `TZ=Africa/Cairo`. Default is UTC.

## HTTPS (strongly recommended on a real network)
Passwords and sessions travel over the network, so put the app behind a reverse proxy with HTTPS
(Caddy, nginx, Traefik, IIS ARR). Then set in a `.env` file next to `docker-compose.yml`:
```
AM_HTTPS=true
AM_TRUST_PROXY=true
AM_ALLOWED_HOSTS=assets.mycompany.com
```
Example Caddyfile:
```
assets.mycompany.com {
    reverse_proxy localhost:5222
}
```

## Upgrading
```bash
git pull   # or unzip the new release over the folder
docker compose up -d --build
```
Database migrations run automatically on start and are preceded by a backup. Release notes: `CHANGELOG.md`.

## Useful commands
```bash
docker compose logs -f assetmaster
docker compose exec assetmaster python tools/manage.py info
docker compose exec assetmaster python tools/manage.py reset-password <username>
docker compose exec assetmaster python tools/manage.py request-code
```

## Notes
- The container runs as an unprivileged user (uid 10001). If you replace the volume with a host folder, run `chown 10001 <folder>`.
- Changing the server hardware or the instance's `install_id` changes the *deployment ID*; the vendor must issue a new licence.
