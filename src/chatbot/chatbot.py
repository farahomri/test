# src/chatbot/chatbot.py

from .intents import intents

def handle_user_input(intent, **kwargs):
    if intent in intents:
        response_function = intents[intent]
        return response_function(**kwargs)
    return "Sorry, I didn't understand that."

# Example usage:
# response = handle_user_input("assigned_technician", schedule_file="path/to/schedule.csv", order_id="123456")
# print(response)

#%%
