# Instructions for Google Calendar Integration

To let Elijah access your calendar, follow these steps:

1.  **Create a Google Cloud Project:**
    - Go to the [Google Cloud Console](https://console.cloud.google.com/).
    - Create a new project named "Lucio AI".

2.  **Enable Calendar API:**
    - In the sidebar, go to **APIs & Services > Library**.
    - Search for "Google Calendar API" and click **Enable**.

3.  **Configure OAuth Consent Screen:**
    - Go to **APIs & Services > OAuth consent screen**.
    - Choose **External** (unless you have a Workspace domain).
    - Fill in the required app info (App name: Lucio AI, your email).
    - In **Scopes**, add `.../auth/calendar` and `.../auth/calendar.events`.
    - Add your own email as a **Test User**.

4.  **Create Credentials:**
    - Go to **APIs & Services > Credentials**.
    - Click **Create Credentials > OAuth client ID**.
    - Application type: **Desktop app**.
    - Name: "Lucio Desktop".
    - Click **Create**, then download the JSON.
    - **Rename the file to `credentials.json`** and place it in this project's root folder.

Once you've done this, Elijah will be able to manage your schedule!
