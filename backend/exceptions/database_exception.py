import os

import oracledb


class DatabaseManager:


    def __init__(self):

        self.connection=None



    def connect(self):

        self.connection = oracledb.connect(
            user=os.getenv("ORACLE_USER", "system"),
            password=os.getenv("ORACLE_PASSWORD", ""),
            dsn=os.getenv("ORACLE_DSN", "localhost/XEPDB1")
        )

        return self.connection



    def close(self):

        if self.connection:

            self.connection.close()