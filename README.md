# Step Function Producer/Consumer Example
### Lambdas
* [Producer](functions/producer/app.py)
* [Consumer](functions/consumer/app.py)

### Step Function
* [statemachine.asl.json](statemachine.asl.json)

#### Steps
1. Producer lambda outputs JSON
2. Consumer lambda receives JSON


#### Running state machine steps locally
```
PRODUCER_OUTPUT=$(sam local invoke Producer)
echo $PRODUCER_OUTPUT

CONSUMER_INPUT=$(echo $PRODUCER_OUTPUT | jq -r '.body | fromjson | {data: .data}')
echo $CONSUMER_INPUT
sam local invoke Consumer -e <(echo "$CONSUMER_INPUT")
```

```
(.venv) 🍏 algo (main) ✗ sam local invoke Consumer -e <(echo "$CONSUMER_INPUT")
{"statusCode": 200, "body": "{\"result\": \"Consumer processed: Hello from Producer!\"}"}
```