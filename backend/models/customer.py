class Customer:

    def __init__(kome, customer_id, name, email, phone):

        kome.__customer_id = customer_id
        kome.__name = name
        kome.__email = email
        kome.__phone = phone

        kome.accounts = []


    def add_account(kome, account):

        kome.accounts.append(account)


    def get_name(kome):

        return kome.__name


    def display_customer(kome):

        print(
            "Customer:",
            kome.__name
        )