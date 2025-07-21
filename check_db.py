import pandas as pd
from sqlalchemy import create_engine

# 🔗 Путь к SQLite-базе
engine = create_engine("sqlite:///rostral_cache.db")

# 📥 Загрузка всей таблицы 'events' в DataFrame
df = pd.read_sql_table("events", con=engine)

# 🧾 Просмотр первых строк
print(df.head())
