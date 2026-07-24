# SirKomeBankSystem

A full-stack **Microfinance Banking System (MFB)** developed using **FastAPI** for the backend and **React (Vite)** for the frontend. The application simulates the core operations of a microfinance bank, including customer registration, secure authentication, account management, fund transfers, and transaction history.

---

## Features

### Customer Management
- Customer registration
- Secure login and authentication
- User profile management

### Account Management
- Automatic account number generation
- Account balance inquiry
- Savings and Current account support

### Transactions
- Deposit funds
- Withdraw funds
- Transfer money between accounts
- Transaction history
- Balance updates in real time

### Security
- PIN hashing
- Token-based authentication
- Input validation
- Exception handling
- Audit logging

### Admin Features
- Customer management
- Transaction monitoring
- Audit logs

---

# Project Structure

```
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
- JWT Authentication
- Hashlib
- Uvicorn

## Frontend

- React
- Vite
- JavaScript
- Axios
- CSS

---

# Installation

## Clone the repository

```bash
git clone https://github.com/Sir-Kome/SirKomeBankSystem.git
```

Go into the project directory.

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

Backend runs at:

```
http://127.0.0.1:8000
```

Swagger documentation:

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

# API Endpoints

Examples include:

## Authentication

- Register
- Login

## Customer

- Get Profile
- Update Profile

## Banking

- Deposit
- Withdraw
- Transfer
- Check Balance
- View Transactions

---

# Security

The application implements several security measures including:

- Password hashing
- PIN hashing
- Token-based authentication
- Protected API endpoints
- Input validation
- Exception handling
- Audit logging

---

# Future Improvements

- PostgreSQL support
- Email verification
- SMS notifications
- Two-Factor Authentication (2FA)
- Loan management
- Card management
- Mobile banking application
- Admin analytics dashboard

---

# Screenshots

Add screenshots of:

- Login page
- Dashboard
- Transfer page
- Transaction history
- Balance page

Example:

```
screenshots/
    login.png
    dashboard.png
    transfer.png
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

This project is intended for educational and learning purposes.