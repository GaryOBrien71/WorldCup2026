# World Cup 2026 Streamlit Supabase update

Upload `app_database.py` to your GitHub repository.

Edit your existing `requirements.txt` and add this line:

```txt
supabase>=2.0
```

In Streamlit Cloud, change the app's main file path to:

```txt
app_database.py
```

Create a Supabase table using the SQL in `supabase_setup.sql`.

Then add these Streamlit Cloud secrets:

```toml
SUPABASE_URL = "https://YOUR-PROJECT.supabase.co"
SUPABASE_KEY = "YOUR-SUPABASE-SERVICE-ROLE-KEY"
STATE_ID = "family"
APP_PASSWORD = "choose-a-family-password"
```

Never commit the Supabase key or password to GitHub.
