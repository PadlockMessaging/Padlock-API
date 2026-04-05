<img width="75" height="75" alt="PadlockMP-02" src="https://github.com/user-attachments/assets/deae8bc7-4106-45df-bdd4-40ee1f289555" /></img>
# Introduction
Padlock Messaging is an E2EE messaging application utilizing the **Signal Protocol** by **Signal Foundation**, featuring **PQXDH for post-quantum secure session establishment** and the **Triple Ratchet for ongoing message encryption**.

> [!WARNING]
> **This program is still in development therefore messaging and encryption functions are not yet implemented.**

# Architecture
## Data security
Padlock Messaging, both client and API side, utilizes cryptography.

### Client side information
- Information such as contacts, messages and session data are encrypted within SQLCipher databases.
- SQLCipher databases are secured with a random generated key saved within the operating system's secure keys manager. (e.g Android Keystore, iOS Keychain)

### Server side information

- User information consists of UUID, phone number, Firebase user ID and registration lock.
- Phone numbers are salted and hashed with SHA-256 prior registration. Registration locks are hashed with Argon2ID for security against brute force attacks in case of a data leak.
- Session information consists of UUID, refresh token, JTI and revocation status.
- Refresh and JTI tokens rotate every call to the token endpoint to refresh the access token to continue access.

> [!IMPORTANT]
> Padlock Messaging utilizes **Google Firebase** services for notification transaction and authentication.
> 
> Therefore your plaintext phone number is stored on **Google Firebase**.

## Authentication and Authorization
1. Phone number is entered.
2. Phone number is sent to Firebase services to initiate a verification session.
3. User receives the SMS code for verification, as per the verification session.
4. User sends the SMS code to the Firebase to sign in.
5. Firebase signs in the user and returns a id_token which then the client returns the id_token to the API server for authorization.
6. API server returns access_token and refresh_token to initiate the session.
7. The client saves access_token and refresh_token to application root using SQLCipher, with the encryption key client generated and saved to the operating system's secure storage.

## Messaging
1. User queries another phone number by clicking on the floating button.
2. When it's a match, a chat page will show.
3. User initiates a WebSocket with the recipient via the API server.
4. Client then invokes the Signal Protocol to initiate keys and encrypt the message.
5. Ciphertext is sent through the open WebSocket.
    - If the WebSocket is open, user will immediately receive the message.
    - If not, the WebSocket will call FCM function to send a notification to the recipient. Then recipient automatically opens a WebSocket to receive pending messages.

# Installation
## Prerequisites

| Name | Version |
| :--- | :---- |
| Python | 3.14.3 |
| pip | 26.0.1 |
| PostgreSQL | 18.3 |

## Installation steps
1. Download and install standalone Python from https://www.python.org/downloads/
2. Update pip by ```python -m pip install --upgrade pip```
3. Download PostgresSQL from https://www.postgresql.org/download/
   - For Linux, follow additional steps
4. Configure PostgresSQL via pgAdmin4

   > **Note:** During **development**, using an empty password is recommended for the PostgresSQL. No security measures need to be taken here since it's local without having any ports exposed. During **production**, password or secrets manager is mandatory.  

5. Create database ```padlock-db```
6. Go into cloned repository directory and run ```pip install -r requirements.txt```
7. Rename ```.env.example``` to ```.env```
8. Generate ```SECRET_KEY``` with ```openssl rand -hex 32```
9. Generate ```SALT``` with:
    ```python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(24)).decode())"```
10. Fill in ```DB``` with ```postgresql://postgres@localhost:5432/padlock-db```
    
    > **Note:** If you set a password, replace with **postgresql://postgres:yourpassword@localhost:5432/padlock-db**
    
11. Download your Firebase secret from Firebase Console
12. Create a ```src/secrets``` directory
13. Move your Firebase secret JSON there
14. Insert ```src/secrets/{json_name}```to ```FIREBASE_SECRET```
15. Run ```alembic upgrade head```
16. Run ```cd src```
17. Run ```uvicorn main:app --host 0.0.0.0 --port 8000 --reload```

# Security policy
Please check for SECURITY.md for the security policy.

# Contributions
Sponsorships and code contributions are highly appreciated. 

Contributions and transparency about security are the main reasons why Padlock Messaging is open source.

# License
Padlock Messaging is licensed with GNU General Public License 3.0. Check LICENSE for more information.
