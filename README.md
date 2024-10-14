Steps
1. Create ExtendedNewOrder
1. Place or Simulate to get ExtendedPlacedOrder
1. Save ExtendedPlacedOrder to DDB





TRADERSYNC
    FOR EACH LEG
        Market: OPTIONS
        Portfolio: My Portfolio
        Symbol: SPX
        Action: BUY
        Spread: SINGLE
        Call/Put: PUT
        Date:
        Time:
        Exp Date:
        Share / Contracts:
        Price:
        Strike:
        Commission:
        Fees:




















## Components
* TastyTrade API
* Tastyware/Tastytrade Python Lib

## Extensions
* ExtendedNewOrder 
    * Attributes
        * underlying_symbol
    * Methods
        * create
            * Gets greeks, quotes, and builds NewOrder
        * validate
            * Checks BPR, etc
* ExtendedPlacedOrder
    * Methods
        * from_response
        * **save_to_dynamodb**
        * **to_csv_row**





aws dynamodb create-table \
    --table-name Orders \
    --attribute-definitions AttributeName=id,AttributeType=S \
    --key-schema AttributeName=id,KeyType=HASH \
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