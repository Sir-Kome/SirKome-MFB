from models.savings_account import SavingsAccount
from models.current_account import CurrentAccount
from models.customer import Customer
from models.transaction import Transaction



customer = Customer(
    1,
    "Kome",
    "kome@gmail.com",
    "08000000000"
)



savings = SavingsAccount(
    "SA001",
    50000
)



current = CurrentAccount(
    "CA001",
    100000
)



customer.add_account(savings)



savings.deposit(20000)


print(
    "Savings Balance:",
    savings.get_balance()
)



print(
    "Savings Interest:",
    savings.calculate_interest()
)



print(
    "Current Interest:",
    current.calculate_interest()
)



transaction = Transaction(
    1,
    "Deposit",
    20000
)


transaction.show_transaction()