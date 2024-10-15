# from pydantic import BaseModel
# import boto3
# from typing import ClassVar
# import uuid

# class Trade(BaseModel):
#     trade_id: str
#     portfolio: str
#     entry_order_id: str
#     entry_order_status: str
#     strategy: str
#     symbol: str
#     # legs: List[Leg]

#     @classmethod
#     def from_entry_order(cls, entry_order, strategy: str, symbol: str, portfolio: str):
#         return cls(
#             trade_id=str(uuid.uuid4()),
#             entry_order_id=str(entry_order.id),  # Convert to string
#             entry_order_status=entry_order.status,
#             strategy=strategy,
#             symbol=symbol,
#             portfolio=portfolio,
#             # legs=placed_order.legs
#         )

#     def save_to_ddb(self, table_name: str = 'Trades'):
#         dynamodb = boto3.resource('dynamodb')
#         table = dynamodb.Table(table_name)
#         item = self.model_dump(mode='json')
#         return table.put_item(Item=item)

#     class Config:
#         json_encoders = {
#             # Add any custom encoders if needed
#         }







