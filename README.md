aws dynamodb create-table \
    --table-name Orders \
    --attribute-definitions AttributeName=order_id,AttributeType=S \
    --key-schema AttributeName=order_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-2




my-project/
├── template.yaml
├── src/
│   ├── function1/
│   │   ├── app.py
│   │   └── template.yaml
│   └── OptionStrat/
│       ├── app.py
│       └── template.yaml