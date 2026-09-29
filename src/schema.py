SCHEMAS={
'customers':{'customer_id':'int','alias':'str','joined_date':'date'},
'categories':{'category_id':'int','name':'str'},
'menu':{'item_id':'int','category_id':'int','name':'str','price':'float','unit_cost':'float','available':'int','introduced_date':'date'},
'locations':{'location_id':'int','name':'str','region':'str'},
'promotions':{'promotion_id':'int','name':'str','start_date':'date','end_date':'date','discount':'float'},
'orders':{'order_id':'int','customer_id':'int','location_id':'int','date':'date','channel':'str','promotion_id':'int','status':'str'},
'order_items':{'line_id':'int','order_id':'int','item_id':'int','quantity':'float','unit_price':'float','discount':'float'},
'pricing_history':{'price_id':'int','item_id':'int','effective_date':'date','price':'float'},
'ratings':{'rating_id':'int','order_id':'int','customer_id':'int','item_id':'int','location_id':'int','date':'date','rating':'float'},
'inventory':{'inventory_id':'int','date':'date','item_id':'int','location_id':'int','opening':'float','replenishment':'float','prepared':'float','consumed':'float','unit':'str'},
'wastage':{'wastage_id':'int','date':'date','item_id':'int','location_id':'int','quantity':'float','unit_cost':'float','reason':'str','unit':'str'}}
PK={k:next(iter(v)) for k,v in SCHEMAS.items()}
FK={'menu':{'category_id':'categories'},'orders':{'customer_id':'customers','location_id':'locations'},'order_items':{'order_id':'orders','item_id':'menu'},'pricing_history':{'item_id':'menu'},'ratings':{'order_id':'orders','customer_id':'customers','item_id':'menu','location_id':'locations'},'inventory':{'item_id':'menu','location_id':'locations'},'wastage':{'item_id':'menu','location_id':'locations'}}
CHANNELS=['Dine-in','Takeaway','Website/App','Delivery']
