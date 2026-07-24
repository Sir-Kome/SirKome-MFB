from models.savings_account import SavingsAccount

from services.transfer_service import TransferService



account1 = SavingsAccount(
"001",
100000
)



account2 = SavingsAccount(
"002",
50000
)



service = TransferService()



result = service.transfer(
account1,
account2,
20000
)



print(result)


print(
account1.get_balance()
)


print(
account2.get_balance()
)