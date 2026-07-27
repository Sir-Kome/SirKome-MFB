# SirKomeBankSystem

A full-stack **Microfinance Banking System (MFB)** built with **FastAPI** (Backend) and **React + Vite** (Frontend). The application simulates the core operations of a modern microfinance bank by allowing customers to register, securely authenticate, manage their accounts and wallets, transfer funds, and view transaction history through a responsive web interface.

---

# 🚀 Features

## 👤 Customer Management

- Customer registration
- Secure login and authentication
- Automatic account number generation
- Automatic wallet creation
- NIN validation
- BVN validation

---

## 💼 Wallet & Account Management

- Wallet linked to every customer account
- Wallet balance management
- Account balance inquiry
- Real-time balance updates

---

## 💸 Banking Operations

- Transfer money between customer wallets
- Transaction PIN verification
- Transaction history
- Debit and credit transaction records

---

## 🔒 Security

- SHA-256 password hashing
- SHA-256 transaction PIN hashing
- Custom HMAC-SHA256 signed Access Token authentication
- Access token expiration
- HTTP Bearer authentication
- Parameterized SQL queries
- Input validation
- Exception handling
- Audit logging

---

## 👨‍💼 Admin Features

- Customer management
- Transaction monitoring
- Audit logging

---

# 📂 Project Structure

```text
SirKomeBankSystem/
│
├── backend/
│   ├── database/
│   ├── exceptions/
│   ├── models/
│   ├── security/
│   ├── services/
│   ├── main.py
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── ...
│
├── screenshots/
│   ├── login.png
│   ├── register.png
│   ├── dashboard.png
│   ├── wallet.png
│   ├── transfer.png
│   ├── transactions.png
│   └── swagger.png
│
├── README.md
└── .gitignore
```

---

# 🛠 Technologies Used

## Backend

- Python
- FastAPI
- SQLite
- SQLite3
- Hashlib
- HMAC-SHA256
- HTTP Bearer Authentication
- Uvicorn

## Frontend

- React
- Vite
- JavaScript
- Axios
- CSS

---

# 🔐 Authentication Flow

1. Customer registers.
2. A unique account number is generated.
3. A customer wallet is automatically created.
4. Customer logs in using email and password.
5. Password is verified using SHA-256 hashing.
6. Backend generates a signed Access Token.
7. React stores the Access Token.
8. Every protected request sends:

```http
Authorization: Bearer <Access Token>
```

9. Backend verifies:

- Token signature
- Token expiration
- Customer identity

10. If valid, access is granted.

---

# 💼 Wallet Flow

```text
Customer Registration
        │
        ▼
Create Customer
        │
        ▼
Generate Account Number
        │
        ▼
Create Wallet
        │
        ▼
Initialize Wallet Balance
        │
        ▼
Registration Successful
```

---

# 💸 Transfer Flow

```text
Customer Initiates Transfer
        │
        ▼
Verify Access Token
        │
        ▼
Validate Sender
        │
        ▼
Validate Receiver
        │
        ▼
Verify Transaction PIN
        │
        ▼
Check Wallet Balance
        │
        ▼
Debit Sender Wallet
        │
        ▼
Credit Receiver Wallet
        │
        ▼
Record Debit Transaction
        │
        ▼
Record Credit Transaction
        │
        ▼
Transfer Successful
```

---

# ⚙️ Installation

## Clone the Repository

```bash
git clone https://github.com/Sir-Kome/SirKomeBankSystem.git
```

Navigate into the project folder.

```bash
cd SirKomeBankSystem
```

---

# Backend Setup

Navigate to the backend folder.

```bash
cd backend
```

Create a virtual environment.

```bash
python -m venv venv
```

Activate the virtual environment.

### Windows

```bash
venv\Scripts\activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Run the backend.

```bash
uvicorn main:app --reload
```

Backend runs at:

```
http://127.0.0.1:8000
```

Swagger Documentation:

```
http://127.0.0.1:8000/docs
```

---

# Frontend Setup

Open another terminal.

Navigate to the frontend folder.

```bash
cd frontend
```

Install dependencies.

```bash
npm install
```

Run the application.

```bash
npm run dev
```

Frontend runs at:

```
http://localhost:5173
```

---

# 🌐 API Endpoints

### Authentication

- Register
- Login

### Wallet

- View Wallet
- Check Wallet Balance

### Banking

- Transfer Funds
- View Transaction History

---

# 🔒 Security Overview

The application implements multiple security mechanisms:

- SHA-256 Password Hashing
- SHA-256 Transaction PIN Hashing
- Custom HMAC-SHA256 Signed Access Tokens
- Access Token Expiration
- HTTP Bearer Authentication
- Protected API Endpoints
- Parameterized SQL Queries
- Input Validation
- Exception Handling
- Audit Logging

---

# 📸 Screenshots

## Login Page

![Login Page](screenshots/login.png)

---

## Registration Page

![Registration Page](screenshots/register.png)

---

## Customer Dashboard

![Dashboard](screenshots/dashboard.png)

---

## Wallet

![Wallet](screenshots/wallet.png)

---

## Transfer Page

![Transfer Page](screenshots/transfer.png)

---

## Transaction History

![Transaction History](screenshots/transactions.png)

---

## Swagger API Documentation

![Swagger](screenshots/swagger.png)

---

# 🚀 Future Improvements

- Refresh Token implementation
- PostgreSQL support
- Redis session storage
- Email verification
- SMS notifications
- Two-Factor Authentication (2FA)
- Loan management
- Card management
- QR code payments
- Mobile banking application
- Analytics dashboard
- Docker deployment
- Cloud hosting (AWS, Azure, or Google Cloud)

---

# 👨‍💻 Author

**Oghenekome Isioro**

Computer and Information Technology

Veritas University Abuja

GitHub: https://github.com/Sir-Kome

---

# 📄 License

This project was developed for educational and learning purposes. It demonstrates the design and implementation of a secure Microfinance Banking System using FastAPI, React, and SQLite.