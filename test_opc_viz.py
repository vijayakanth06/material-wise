"""Quick test for OPC-53 Grade Cement visualization"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from agentapp.product_matcher import find_matching_product
from agentapp.visualizations import create_comprehensive_visualization
import pandas as pd

# Load data
csv_path = 'data/price_index.csv'
product = 'OPC-53 Grade Cement'

print(f"Testing visualization for: {product}")
print("=" * 60)

# Find matching product
df = pd.read_csv(csv_path)
mask = find_matching_product(df, product, 'comm_name')

if mask.sum() > 0:
    matched_name = df[mask]['comm_name'].iloc[0]
    print(f"✓ Matched to CSV product: '{matched_name}'")
    
    # Get historical data
    sub = df[mask]
    index_cols = [c for c in sub.columns if c.startswith('indx')]
    df_long = sub.melt(
        id_vars=['comm_name','comm_code','comm_wt'], 
        value_vars=index_cols,
        var_name='month', 
        value_name='price_index'
    )
    df_long['month'] = df_long['month'].str.replace('indx','', regex=False)
    df_long['date'] = pd.to_datetime(df_long['month'], format='%m%Y', errors='coerce')
    df_long = df_long.dropna(subset=['date']).sort_values('date').tail(12)
    
    print(f"✓ Historical data: {len(df_long)} months")
    print(f"  Latest price index: {df_long['price_index'].iloc[-1]}")
    
    # Create visualization
    prediction = {
        'trend': 'UP',
        'probability': 0.75,
        'predicted_value': df_long['price_index'].iloc[-1] * 1.05
    }
    
    scraper_results = {
        'buildersmart': {'status': 'available', 'median': 400},
        'indiamart': {'status': 'available', 'median': 420}
    }
    
    viz = create_comprehensive_visualization(
        df_long, prediction, scraper_results, product
    )
    
    if viz.get('line_graph') and viz.get('bar_graph'):
        print(f"✓ Visualizations generated successfully!")
        print(f"  Line graph: {len(viz['line_graph'])} bytes")
        print(f"  Bar graph: {len(viz['bar_graph'])} bytes")
        
        # Save test images
        import base64
        os.makedirs('test_outputs', exist_ok=True)
        
        for name, data in [('line', viz['line_graph']), ('bar', viz['bar_graph'])]:
            img_data = base64.b64decode(data.replace('data:image/png;base64,', ''))
            with open(f'test_outputs/{product.replace(" ", "_").replace("-", "_")}_{name}.png', 'wb') as f:
                f.write(img_data)
        
        print(f"✓ Test images saved to test_outputs/")
        print("\n" + "=" * 60)
        print("SUCCESS: OPC-53 Grade Cement visualization is working!")
    else:
        print("✗ Visualization generation failed")
        print(f"  Error: {viz.get('error', 'Unknown error')}")
else:
    print(f"✗ No matching product found for: {product}")
