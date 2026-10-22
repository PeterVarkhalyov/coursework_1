from src.processing_views import get_transactions
from src.services import get_transactions_search_person, get_transactions_total_person

PERSON = "Дмитрий Шершнёв"
transactions = get_transactions()

result = get_transactions_search_person(transactions, PERSON)
print(result)

total = get_transactions_total_person(transactions)
print(total)
