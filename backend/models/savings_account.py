from models.account import Account



class SavingsAccount(Account):


    def calculate_interest(kome):

        interest = kome.get_balance() * 0.05

        return interest