import json

def lambda_handler(event, context):
    # Log the incoming event from the Producer
    print(type(event))
    print("Received message:", event)

    parsed_event = json.loads(event)
    processed_message = f"Consumer processed: {parsed_event['data']}"
    print(processed_message)
    
    return json.dumps({"result": processed_message})