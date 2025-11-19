# Line Bot for NCU Campus QA

This LINE bot provides a question-answering service for NCU campus-related inquiries.

## Setup

1.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

2.  **Set up environment variables:**

    Create a `.env` file in this directory. You can use `.env.example` as a template:

    ```bash
    cp .env.example .env
    ```

    Then, fill in the required values in the `.env` file:

    -   `LINE_CHANNEL_ACCESS_TOKEN`: Your LINE channel access token.
    -   `LINE_CHANNEL_SECRET`: Your LINE channel secret.
    -   `LLAMA_API_URL`: The URL for your Llama API endpoint.

3.  **Run the application:**

    ```bash
    python app.py
    ```
