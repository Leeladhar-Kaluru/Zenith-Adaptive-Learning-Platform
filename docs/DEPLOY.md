# Deploying ZENITH (free: Vercel Hobby + Supabase + Groq + Backblaze)

Do these in order. Never paste secret values into chat or commit them.

## 1. Push the code
The code is on GitHub `origin` (branch `master`). Vercel deploys from it.

## 2. Create the Vercel project
1. vercel.com -> Add New -> Project -> import the GitHub repository. Leave the root directory as the repository root; `vercel.json` sets the build.
2. Framework preset: Other. Do not deploy yet; add environment variables first (step 3).

## 3. Environment variables (Vercel -> Settings -> Environment Variables, Production)
| Name | Value |
|---|---|
| APP_ENV | production |
| DATABASE_URL | Supabase **transaction pooler** URI (port 6543), `postgresql+psycopg://...` |
| DB_SCHEMA | zenith |
| SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, SUPABASE_SECRET_KEY | from Supabase -> Project Settings -> API |
| GROQ_API_KEY | your Groq key |
| ENABLE_REMOTE_AI | true |
| FRONTEND_ORIGINS | your Vercel URL, e.g. https://zenith.vercel.app |
| ZENITH_DEV_AUTH | false |

Use the same values as `backend/.env` except DATABASE_URL (pooler port 6543 for serverless; keep 5432 locally for migrations).

## 4. Supabase Auth
Authentication -> URL Configuration: set Site URL to your Vercel URL and add it to Redirect URLs. Decide whether email confirmation stays on (recommended).

## 5. Deploy, then check
Open `https://<your-app>/api/v1/health` (or `/api`) and the home page.

## 6. Make yourself the reviewer
Sign up on the live site, then on your computer (with production DATABASE_URL, session pooler 5432):
```
cd backend
python -m app.cli import ../content
python -m app.cli promote you@example.com reviewer
```
Open `/review`, read each lesson, approve and publish. Students see nothing until you do.

## 7. Backups
GitHub repo -> Settings -> Secrets and variables -> Actions: add `BACKUP_DATABASE_URL` (session pooler URI), `B2_KEY_ID`, `B2_APP_KEY`, `B2_BUCKET` (zenith-media), `BACKUP_KEY`. Run the "Weekly encrypted backup" workflow once by hand and confirm it is green. Save `BACKUP_KEY` in a password manager.

## 8. Rotate the Backblaze key
The first application key was pasted in chat. In Backblaze create a new key limited to the `zenith-media` bucket, update `backend/.env` and the GitHub secrets, then delete the old key.

## 9. Later (needs your explicit approval)
Dropping the legacy SETU tables in the `public` schema.
