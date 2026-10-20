from src.views import get_events_response

# , get_main_response)

# 2021-12-25  16:42:04
# result = get_main_response("2021-12-25  16:42:04")
# print(result)

# 2021-12-31 16:44:00
result = get_events_response("2021-12-31 16:44:00", "M")

print(result)
