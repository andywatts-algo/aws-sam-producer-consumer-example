import json

def lambda_handler(event, context):
    # Generate a message
    message = {"data": "Hello from Producer!"}
    
    # Log the message
    print("Produced message:", message)
    
    return json.dumps(message)