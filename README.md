# SirKomeBankSystem

A full-stack **Microfinance Banking System (MFB)** developed using **FastAPI** for the backend and **React (Vite)** for the frontend.

The application simulates the core operations of a modern microfinance bank, including customer registration, secure authentication, wallet creation, account management, fund transfers, transaction history, and administrative operations.

---

# Features

## Customer Management

- Customer registration
- Secure login
- User profile management
- NIN validation
- BVN validation
- Automatic customer wallet creation

---

## Wallet & Account Management

- Automatic account number generation
- Automatic wallet creation for every customer
- Wallet balance management
- Account balance inquiry
- Savings and Current account support
- Wallet linked to customer account

---

## Banking Operations

- Deposit funds
- Withdraw funds
- Transfer money between customer wallets
- Real-time wallet balance updates
- Account balance synchronization
- Transaction history
- Debit and credit transaction records

---

## Authentication & Security

- Password hashing (SHA-256)
- Transaction PIN hashing
- Custom HMAC-SHA256 signed Access Tokens
- Token expiration
- Protected API endpoints
- HTTP Bearer Authentication
- Input validation
- Parameterized SQL queries
- Exception handling
- Audit logging

---

## Admin Features

- Customer management
- Transaction monitoring
- Audit logs
- Administrative transfers

---

# Project Structure

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
├── README.md
└── .gitignore
```

---

# Technologies Used

## Backend

- Python
- FastAPI
- SQLite
- HMAC-SHA256 Access Token Authentication
- HTTP Bearer Authentication
- Hashlib
- SQLite3
- Uvicorn

## Frontend

- React
- Vite
- JavaScript
- Axios
- CSS

---

# Authentication Flow

1. Customer registers.
2. Customer wallet is automatically created.
3. Customer logs in using email and password.
4. Password is verified using SHA-256 hashing.
5. Backend generates a signed Access Token.
6. React stores the Access Token.
7. Every protected request sends:

```
Authorization: Bearer <Access Token>
```

8. Backend verifies:

- Token signature
- Token expiration
- Customer identity

9. If valid, access is granted.

---

# Wallet Flow

```
Customer Registration
        │
        ▼
Create Customer
        │
        ▼
Generate Account Number
        │
        ▼
Create Customer Wallet
        │
        ▼
Initialize Wallet Balance
        │
        ▼
Registration Complete
```

---

# Transfer Flow

```
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
Record Transactions
        │
        ▼
Return Success Response
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/Sir-Kome/SirKomeBankSystem.git
```

Navigate into the project.

```bash
cd SirKomeBankSystem
```

---

# Backend Setup

```bash
cd backend
```

Create a virtual environment.

```bash
python -m venv venv
```

Activate it.

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

Backend:

```
http://127.0.0.1:8000
```

Swagger API Documentation:

```
http://127.0.0.1:8000/docs
```

---

# Frontend Setup

Open another terminal.

```bash
cd frontend
```

Install packages.

```bash
npm install
```

Run the frontend.

```bash
npm run dev
```

Frontend:

```
http://localhost:5173
```

---

# API Endpoints

## Authentication

- Register
- Login

## Wallet

- View Wallet
- Wallet Balance

## Customer

- Get Profile
- Update Profile

## Banking

- Deposit
- Withdraw
- Transfer
- Check Balance
- Transaction History

---

# Security

The system implements multiple security mechanisms:

- SHA-256 Password Hashing
- SHA-256 Transaction PIN Hashing
- Custom HMAC-SHA256 Access Tokens
- Token Expiration
- HTTP Bearer Authentication
- Protected Endpoints
- Parameterized SQL Queries
- Input Validation
- Exception Handling
- Audit Logging

---

# Future Improvements

- Refresh Tokens
- PostgreSQL
- Redis Session Storage
- Email Verification
- SMS Notifications
- Two-Factor Authentication (2FA)
- Loan Management
- Card Management
- QR Code Payments
- Mobile Banking Application
- Admin Analytics Dashboard

---

# Screenshots

Include screenshots of:

- Login Page
- Customer Dashboard
- Wallet Overview
- Transfer Page
- Transaction History
- Profile Page
- Admin Dashboard

Example:

```
screenshots/
    login.png
    dashboard.png
    wallet.png
    transfer.png
    transactions.png
```

---

# Author

**Oghenekome Isioro**

Computer and Information Technology

Veritas University Abuja

GitHub:

https://github.com/Sir-Kome

---

# License

This project is intended for educational, research, and learning purposes.