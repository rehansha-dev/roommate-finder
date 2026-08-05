# Roommate Finder

## Run locally

The easiest way is to double-click **Start Roommate Finder.bat** in this folder.
Keep its black command window open, then visit http://127.0.0.1:10000.

Alternatively, run:

```powershell
cd "C:\Users\REHAN\Documents\Codex\2026-08-05\from-flask-import-flask-render-template\outputs\roommate-finder"
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
.\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:10000 in a browser.

The admin page is at `/admin`. Its default password is `822711`; set an `ADMIN_PASSWORD` environment variable before running the app to change it.

## Publish online with Render

1. Create a GitHub repository and upload this folder (do not upload `.venv` or `database.db`).
2. In Render, create a **Postgres** database and copy its internal connection URL.
3. Create a **Web Service** from the GitHub repository. Render reads `render.yaml` and installs the required packages.
4. In the Web Service's Environment section, add `DATABASE_URL` using the Postgres connection URL. Replace `ADMIN_PASSWORD` with a strong private password.
5. Deploy. Render gives you a public `https://...onrender.com` address that works on phones and laptops.

`DATABASE_URL` is intentionally not used on your laptop, so local use continues to store data in `database.db`.
