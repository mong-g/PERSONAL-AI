# Lucio - Personal AI

Lucio is a personal AI assistant that connects to Facebook Messenger.

## Getting Started

To run Lucio, you need to provide your Facebook session cookies in the form of an `app_state.json` file.

### Exporting app_state.json

1.  **Install a Cookie Export Extension:**
    *   Install [C3C-FB-STATE](https://chrome.google.com/webstore/detail/c3c-fb-state-utility/pmlmgekjfhhfioofdfnphgeicidnbiky) or [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg) in your Chrome browser.
2.  **Log into Facebook:**
    *   Go to [facebook.com](https://www.facebook.com) and ensure you are logged into the account you want the bot to use.
3.  **Export Cookies:**
    *   Click on the extension icon and select the option to export cookies as **JSON**.
4.  **Save the File:**
    *   Save the exported JSON content as `app_state.json` in the root of the project.
5.  **Configure Environment Variables:**
    *   Update your `.env` file with your Facebook User ID:
        ```env
        USER_FB_ID=your_facebook_user_id_here
        ```

### Running the Bot

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *Note: You may need to install `libmagic` on your system (e.g., `brew install libmagic` on macOS or `sudo apt-get install libmagic1` on Linux) as it is required by the `python-magic` dependency.*

2.  **Start Lucio:**
    ```bash
    python lucio.py
    ```

Once started, Lucio will listen for messages. In Phase 1, it will echo back any messages sent to it by the authorized user (defined by `USER_FB_ID`).
