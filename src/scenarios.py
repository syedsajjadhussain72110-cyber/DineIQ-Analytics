import math

def simulate(row,price_change=0,discount=0,promotion_frequency=0,demand_change=0,preparation_change=0,waste_rate=None,remove=False,elasticity=-.5):
 v=[price_change,discount,promotion_frequency,demand_change,preparation_change,elasticity]+([] if waste_rate is None else [waste_rate])
 if not all(math.isfinite(float(x)) for x in v):raise ValueError('Finite numeric values required')
 if not -.9<=price_change<=2 or not 0<=discount<=.9 or not 0<=promotion_frequency<=1 or not -.95<=demand_change<=3 or not -.95<=preparation_change<=3:raise ValueError('Scenario outside supported range')
 if waste_rate is not None and not 0<=waste_rate<=1:raise ValueError('Waste rate must be between 0 and 1')
 q=float(row['quantity']);revenue=float(row['revenue']);cost=float(row['cost']);price=revenue/max(q,1);unit_cost=cost/max(q,1);new_price=price*(1+price_change)*(1-discount*promotion_frequency);demand=0 if remove else q*(new_price/max(price,.01))**elasticity*(1+demand_change);prepared=float(row.get('prepared',q))*(1+preparation_change);waste=max(0,prepared-demand) if waste_rate is None else prepared*waste_rate
 return {'estimate':True,'baseline_revenue':revenue,'estimated_revenue':demand*new_price,'estimated_demand':demand,'estimated_waste':waste,'estimated_contribution':demand*(new_price-unit_cost),'estimated_after_waste':demand*(new_price-unit_cost)-waste*unit_cost,'revenue_change':demand*new_price-revenue,'assumptions':f'Elasticity {elasticity:.2f}; constant unit cost; no capacity limit; discount weighted by exposure; observational sensitivity, not a causal experiment.'}
