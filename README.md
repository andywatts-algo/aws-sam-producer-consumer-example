Functions
ExampleFunction

OpeningOrderFunction

OpeningOrderFillFunction
ProfitTargetOrderFunction
StopLossOrderFunction
OptionStratFunction





## Examples
### Producer & Consumer
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


# SAM.   Serverless Application Model

### AWS SAM Resources:
- **`AWS::Serverless::Application`** – Nested SAM/CloudFormation app
- **`AWS::Serverless::Function`** – Lambda function
- **`AWS::Serverless::SimpleTable`** – DynamoDB table
- **`AWS::Serverless::StateMachine`** – Step Functions state machine
- **`AWS::Serverless::Api`** – API Gateway (REST API)
- **`AWS::Serverless::HttpApi`** – API Gateway (HTTP API)
- **`AWS::Serverless::LayerVersion`** – Lambda layer
- **`AWS::Serverless::Connector`** – Service connection (e.g., Lambda & S3)

### CloudFormation Resources:
- **`AWS::S3::Bucket`** – S3 bucket
- **`AWS::DynamoDB::Table`** – DynamoDB table
- **`AWS::SNS::Topic`** – SNS topic
- **`AWS::SQS::Queue`** – SQS queue
- **`AWS::IAM::Role`** – IAM role