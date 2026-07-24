from database.database_manager import DatabaseManager


db = DatabaseManager()


connection = db.connect()


print(
"Database connected"
)