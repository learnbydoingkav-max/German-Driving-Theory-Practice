# German Driving Theory Practice

A Streamlit app for German driving theory multiple-choice practice with AI-generated questions and Wikimedia Commons image lookup.

## Deploying to Streamlit Cloud

1. Push this repository to GitHub.
2. In Streamlit Cloud, create a new app from this repo.
3. Set the app entry point to `main.py`.
4. Add the secret key under **Settings > Secrets**:

```toml
OPENROUTER_API_KEY = "your_openrouter_api_key"
```

5. Streamlit Cloud will install dependencies from `requirements.txt` automatically.

## Local development

- Run locally with:

```bash
streamlit run main.py
```

- If you use a local secrets file, place it in `.streamlit/secrets.toml` and do not commit it.
