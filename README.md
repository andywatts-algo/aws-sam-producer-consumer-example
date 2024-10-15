EntryOrderFunction
EntryOrderAdjustFunction
ProfitTargetOrderFunction
StopLossOrderFunction
OptionStratFunction










DRY RUN FLOW
1. Create BullPutSpreadOrder
1. Get quote data
1. Save simulated executions to ddb


LIVE FLOW
1. Create BullPutSpreadOrder
1. Get quote data
1. Place order
1. Monitor order
1. Save executions to ddb




PlacedOrder
* id