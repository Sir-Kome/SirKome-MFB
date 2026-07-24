class BankStaff:


    def __init__(
        kome,
        staff_id,
        username,
        password,
        role
    ):

        kome.staff_id = staff_id
        kome.username = username
        kome.password = password
        kome.role = role



    def login(
        kome,
        username,
        password
    ):


        if (
            username == kome.username
            and
            password == kome.password
        ):

            return True


        return False