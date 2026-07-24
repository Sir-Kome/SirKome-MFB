from abc import ABC, abstractmethod


class Account(ABC):


    def __init__(kome, account_number, balance):

        kome.__account_number = account_number
        kome.__balance = balance



    def deposit(kome, amount):

        if amount <= 0:

            raise ValueError(
                "Invalid deposit"
            )

        kome.__balance += amount



    def withdraw(kome, amount):

        if amount > kome.__balance:

            raise Exception(
                "Insufficient balance"
            )


        kome.__balance -= amount



    def get_balance(kome):

        return kome.__balance



    @abstractmethod
    def calculate_interest(self):

        pass