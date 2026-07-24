import os

import oracledb


class DatabaseManager:


    def connect(self):

        connection = oracledb.connect(
            user=os.getenv("ORACLE_USER", "system"),
            password=os.getenv("ORACLE_PASSWORD", ""),
            dsn=os.getenv("ORACLE_DSN", "localhost/XEPDB1")
        )

        return connection