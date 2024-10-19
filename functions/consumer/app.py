import json

def lambda_handler(event, context):
    print("Received message:", event)

    processed_message = f"Consumer received: {event['data']}"
    print(processed_message)
    
    return {"result": processed_message}