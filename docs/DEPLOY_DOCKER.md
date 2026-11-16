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
`data.db` (database) · `uploads/` · `backups/` · `secrets.json` (secret key) · `config.json` · `install_id`.
- Automatic backup every day at 02:00 and before every upgrade (kept: last 14).
- **Copy the backups folder to another machine regularly.** A backup on the same disk does not protect against disk failure.
```bash
docker compose exec assetmaster python tools/manage.py backup
docker compose cp assetmaster:/data/backups ./backups-copy
```
Restore (stop the app first):
```bash
docker compose stop
docker compose run --rm assetmaster python tools/manage.py restore data_20260101_020000_auto.db
docker compose up -d
```

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
