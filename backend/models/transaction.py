from datetime import datetime



class Transaction:


    def __init__(kome, transaction_id, type, amount):

        kome.transaction_id = transaction_id

        kome.type = type

        kome.amount = amount

        kome.date = datetime.now()



    def show_transaction(kome):

        print(
            kome.type,
            kome.amount,
            kome.date
        )