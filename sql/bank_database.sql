CREATE TABLE Customers(

customer_id NUMBER PRIMARY KEY,

name VARCHAR2(100),

email VARCHAR2(100),

phone VARCHAR2(20),

password VARCHAR2(100)

);

CREATE TABLE Accounts(

account_id NUMBER PRIMARY KEY,

customer_id NUMBER,

account_number VARCHAR2(20),

account_type VARCHAR2(20),

balance NUMBER,


FOREIGN KEY(customer_id)
REFERENCES Customers(customer_id)

);

CREATE TABLE Transactions(

transaction_id NUMBER PRIMARY KEY,

account_id NUMBER,

amount NUMBER,

transaction_type VARCHAR2(20),

transaction_date DATE,


FOREIGN KEY(account_id)
REFERENCES Accounts(account_id)

);

CREATE TABLE Transfers(

transfer_id NUMBER PRIMARY KEY,

sender_account VARCHAR2(20),

receiver_account VARCHAR2(20),

amount NUMBER,

transfer_date DATE

);

CREATE TABLE BankStaff(

staff_id NUMBER PRIMARY KEY,

username VARCHAR2(50),

password VARCHAR2(50),

role VARCHAR2(50)

);

CREATE TABLE AuditLogs(

log_id NUMBER,

action VARCHAR2(100),

log_date DATE

);