from src.readers import get_transactions_from_xls

data = get_transactions_from_xls('data/operations.xlsx')

print(data)