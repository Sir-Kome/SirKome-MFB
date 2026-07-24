from datetime import datetime


class AuditLogger:


    def log(kome, action):

        record = {

        "action":action,

        "time":datetime.now()

        }


        print(record)