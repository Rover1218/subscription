# Subscription Management App

This is a Flask-based web application for managing subscriptions. Users can register, log in, and manage their subscriptions, including adding, deleting, and viewing reminders for upcoming renewals.

## Features

- User registration and authentication
- Add, view, and delete subscriptions
- Automatic renewal date updates based on subscription frequency
- Reminder notifications for upcoming renewals

## Setup

1. Clone the repository:
    ```sh
    git clone https://github.com/yourusername/subscription-app.git
    cd subscription-app
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Create a `.env` file and add your environment variables:
    ```env
    SECRET_KEY=your-secret-key
    MONGO_URI=your-mongo-uri
    ```

5. Run the application:
    ```sh
    python app.py
    ```

6. Open your browser and navigate to `http://127.0.0.1:5000/`.

## Deployment

To deploy the application on Vercel, follow these steps:

1. Install the Vercel CLI:
    ```sh
    npm install -g vercel
    ```

2. Deploy the application:
    ```sh
    vercel
    ```

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.