import json

def lambda_handler(event, context):
    print("Received event:", event)

    # Generate a message
    message = {"data": "Hello from Producer!"}
    print("Output:", message)
    
    return message