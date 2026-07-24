class TransferService:


    def transfer(
        kome,
        sender,
        receiver,
        amount
    ):

        try:

            sender.withdraw(amount)

            receiver.deposit(amount)


            return {
                "status":"success",
                "message":"Transfer completed"
            }


        except Exception as e:

            return {
                "status":"failed",
                "message":str(e)
            }