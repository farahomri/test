import spacy
from transformers import pipeline
from .intents import intents

# Load spaCy model for NER
nlp = spacy.load('en_core_web_sm')

# Load a pre-trained intent detection model using Hugging Face's transformers
classifier = pipeline('zero-shot-classification', model="facebook/bart-large-mnli")

# List of potential intents
intent_labels = [
    "assigned_technician",
    "order_status",
    "list_orders_by_technician",
    "count_in_progress_orders",
    "order_classification",
    "technician_classification",
    "completed_orders"
]

# Function to extract entities using spaCy
def extract_entities(user_input):
    doc = nlp(user_input)
    entities = {}
    for ent in doc.ents:
        if ent.label_ == "CARDINAL":  # Assuming order IDs are numerical
            entities["order_id"] = ent.text
    return entities

# Function to detect the intent of the user using Hugging Face's transformer
def detect_intent(user_input):
    result = classifier(user_input, intent_labels)
    top_intent = result['labels'][0]
    return top_intent

# Function to handle user input
def handle_user_input(user_input):
    # Detect the intent
    intent = detect_intent(user_input)
    print(f"Detected intent: {intent}")

    # Extract entities using spaCy
    entities = extract_entities(user_input)
    print(f"Extracted entities: {entities}")

    # Call the appropriate function based on the detected intent
    if intent in intents:
        response_function = intents[intent]

        # If the intent requires an order_id (such as 'order_status' or 'assigned_technician')
        if intent in ["assigned_technician", "order_status", "order_classification"] and "order_id" in entities:
            return response_function(order_id=entities.get("order_id"))

        # For intents that don't require an order_id (like 'count_completed_orders')
        elif intent in ["count_completed_orders", "count_in_progress_orders"]:
            return response_function()

        # If an intent requiring an order_id is missing it, return a message
        elif intent in ["assigned_technician", "order_status", "order_classification"]:
            return "No order ID found in your request."

        else:
            return response_function()
    else:
        return "Sorry, I didn't understand that."