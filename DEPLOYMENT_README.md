# Deploying the AI Appraisal Prototype Online

This turns the prototype from a laptop-only app into a link you can send to
recruited participants. It covers three things: where the response data is
stored, how the AI key is protected, and how to actually get the app hosted
online via GitHub + Streamlit Community Cloud.

## 1. What changed in the code

- The sidebar no longer asks for an Anthropic API key. The app now reads
  `ANTHROPIC_API_KEY` from Streamlit's secrets store (`st.secrets`), which is
  invisible to participants and only ever set by you, once, in the hosting
  dashboard.
- Responses are no longer written to a local `responses.csv` file. A new
  `storage.py` module appends every submitted row to a Google Sheet you own,
  using a Google Cloud **service account** (a machine identity, not your
  personal Google login). If the Google Sheets secrets are missing —
  e.g. while testing locally without setting anything up — it automatically
  falls back to writing `responses.csv` in the current folder, so nothing
  breaks during local development.
- New file `storage.py` — the storage backend.
- New file `requirements.txt` — the exact Python packages the hosted app
  needs installed (Streamlit reads this automatically).
- New file `secrets.toml.example` — a template showing exactly what to put in
  Streamlit's secrets box. Never commit a real filled-in version of this to
  GitHub.

The CSV column schema is unchanged — same 23 columns as before
(`participant_id`, `nationality`, ... `rubric_notes`), so `Chapter3_Data_Entry_Guide.md`
and `compute_chapter3_results.py` continue to work unmodified. When you
eventually want to run the analysis script, just export the Google Sheet as
CSV first (File → Download → Comma Separated Values in Google Sheets).

## 2. Set up the Google Sheet and service account (do this once)

1. **Create the sheet.** Go to [Google Sheets](https://sheets.google.com) and
   create a new blank sheet. Name it something like `FPR Appraisal Responses`.
   Copy the long ID out of its URL — it's the part between `/d/` and `/edit`:
   `https://docs.google.com/spreadsheets/d/THIS_PART/edit`.
2. **Create a Google Cloud project** (free) at the
   [Google Cloud Console](https://console.cloud.google.com/projectcreate) if
   you don't already have one.
3. **Enable the Google Sheets API** for that project: in the console, search
   for "Google Sheets API" and click Enable.
4. **Create a service account**: in the console, go to
   *IAM & Admin → Service Accounts → Create Service Account*. Give it any
   name (e.g. `fpr-appraisal-writer`). You don't need to grant it any
   project-level roles for this.
5. **Create a key for it**: open the new service account → *Keys* tab →
   *Add Key → Create new key → JSON*. This downloads a `.json` file — treat it
   like a password.
6. **Share the Google Sheet with the service account.** Open the downloaded
   JSON file and copy the `client_email` value (looks like
   `something@your-project.iam.gserviceaccount.com`). Go back to your Google
   Sheet, click *Share*, and share it with that email address as an Editor.
   This is the step people most often forget — without it you'll get a
   permissions error the first time someone submits a response.
7. **Fill in `secrets.toml.example`** using the values from the downloaded
   JSON file (`project_id`, `private_key_id`, `private_key`, `client_email`,
   `client_id`, `token_uri`) plus your sheet's ID as `sheet_id`. Keep the
   `private_key` exactly as downloaded, including the `\n` line breaks.

## 3. Push the code to GitHub

The prototype folder (`app.py`, `storage.py`, `prompt_template.py`,
`synthetic_cases.json`, `requirements.txt`, `secrets.toml.example`) needs to
live in a GitHub repository, because Streamlit Community Cloud deploys
directly from a GitHub repo. Do **not** include a real filled-in
`secrets.toml` in the repo — secrets are entered separately in the Streamlit
dashboard, never committed.

Once the repo is created and the files are pushed (this can be done for you —
see the note in the covering message), the repo is ready to connect to
Streamlit Community Cloud.

## 4. Deploy on Streamlit Community Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with
   your GitHub account.
2. Click **New app**, pick the repository you just pushed, set the branch
   (usually `main`) and the main file path — likely `prototype/app.py` or
   `app.py` depending on the folder structure used.
3. Before or right after deploying, open the app's **Settings → Secrets**
   box and paste in your filled-in secrets — the same content you put in
   `secrets.toml.example`, but with your real values.
4. Click Deploy. Streamlit installs everything from `requirements.txt` and
   gives you a public URL like `https://your-app-name.streamlit.app` — this
   is the link you send to participants.

## 5. Before recruiting real participants

- Do a full test run yourself on the deployed link end to end (Manual
  condition, then AI-Assisted condition) and confirm a new row appears in
  the Google Sheet each time.
- Clear out any test rows from the sheet before real recruitment starts, or
  clearly mark them, so test traffic is never mixed with real participant
  data — this matters for the same academic-integrity reason Appendix H
  flags for the synthetic pilot data.
- Keep the ethics-approval protocol number and consent language visible in
  the app or in your recruitment materials, consistent with what your FPR
  states about ethical approval.

## 6. Ongoing cost

Every AI-Assisted generation calls your Anthropic account (the key is
server-side and shared across all participants). For a study of 8–15
participants doing two conditions each, this is a small number of short
generations — expect a cost of a few dollars at most for the full study, but
it is billed to your own Anthropic account, so it's worth keeping an eye on
usage at [console.anthropic.com](https://console.anthropic.com/).
