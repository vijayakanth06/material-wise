import matplotlib
matplotlib.use('Agg')  # Non-GUI backend for web apps
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import io
import base64
from datetime import datetime

# Base prices (2012 reference year) for common materials in INR
# These are approximate wholesale prices used to convert index to actual price
BASE_PRICES = {
    'cement': 300,  # OPC/PPC cement per 50kg bag
    'steel': 35,    # Steel per kg
    'white cement': 450,  # White cement per 50kg bag
    'slag cement': 290,
    'pozzolana cement': 290,
}

def estimate_base_price(material_name: str) -> float:
    """Estimate base price (2012) for a material based on its name.
    
    Args:
        material_name: Name of the material
        
    Returns:
        Estimated base price in INR
    """
    material_lower = material_name.lower()
    
    # Check for specific material types
    if 'white cement' in material_lower:
        return BASE_PRICES['white cement']
    elif 'slag cement' in material_lower:
        return BASE_PRICES['slag cement']
    elif 'pozzolana' in material_lower or 'ppc' in material_lower:
        return BASE_PRICES['pozzolana cement']
    elif 'cement' in material_lower or 'opc' in material_lower:
        return BASE_PRICES['cement']
    elif 'steel' in material_lower or 'tmt' in material_lower or 'ms' in material_lower:
        return BASE_PRICES['steel']
    else:
        # Default fallback
        return 300

def convert_index_to_price(price_index: float, material_name: str) -> float:
    """Convert price index to estimated actual price.
    
    Args:
        price_index: Price index value (base 2012 = 100)
        material_name: Name of the material
        
    Returns:
        Estimated actual price in INR
    """
    base_price = estimate_base_price(material_name)
    return base_price * (price_index / 100)


def create_prediction_line_graph(historical_data: pd.DataFrame, 
                                 prediction: Dict,
                                 material_name: str) -> str:
    """Create a line graph showing historical price index and prediction.
    
    Args:
        historical_data: DataFrame with 'date' and 'price_index' columns
        prediction: Dict with 'trend', 'probability', 'predicted_value' (optional)
        material_name: Name of the material
        
    Returns:
        Base64 encoded PNG image string
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plot historical data
    ax.plot(historical_data['date'], historical_data['price_index'], 
            marker='o', linewidth=2, markersize=4, label='Historical Price Index',
            color='#2E86AB')
    
    # Add prediction point if available
    if 'predicted_value' in prediction:
        last_date = historical_data['date'].iloc[-1]
        last_value = historical_data['price_index'].iloc[-1]
        pred_value = prediction['predicted_value']
        
        # Draw arrow showing trend
        trend = prediction.get('trend', 'STABLE')
        if trend == 'UP' or trend == '1' or trend == 1:
            color = '#06A77D'
            arrow_label = '↑ Predicted Increase'
        elif trend == 'DOWN' or trend == '-1' or trend == -1:
            color = '#D62828'
            arrow_label = '↓ Predicted Decrease'
        else:
            color = '#F77F00'
            arrow_label = '→ Predicted Stable'
        
        ax.scatter([last_date], [pred_value], color=color, s=200, 
                  zorder=5, label=arrow_label, marker='*')
        ax.annotate(f'{pred_value:.1f}', 
                   xy=(last_date, pred_value),
                   xytext=(10, 10), textcoords='offset points',
                   fontsize=10, color=color, weight='bold')
    
    # Styling
    ax.set_xlabel('Date', fontsize=12, weight='bold')
    ax.set_ylabel('Price Index', fontsize=12, weight='bold')
    ax.set_title(f'Price Index Trend: {material_name}', fontsize=14, weight='bold', pad=20)
    ax.legend(loc='best', framealpha=0.9)
    ax.grid(True, alpha=0.3, linestyle='--')
    
    # Add confidence annotation
    if 'probability' in prediction:
        conf_text = f"Confidence: {prediction['probability']*100:.1f}%"
        ax.text(0.02, 0.98, conf_text, transform=ax.transAxes,
               fontsize=10, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    
    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    return f"data:image/png;base64,{img_base64}"


def create_price_comparison_bar_graph(model_price: Optional[float],
                                     indiamart_price: Optional[float],
                                     buildersmart_price: Optional[float],
                                     material_name: str,
                                     price_type: str = "median") -> str:
    """Create a bar graph comparing prices from three sources.
    
    Args:
        model_price: Predicted price from model
        indiamart_price: Current price from IndiaMART
        buildersmart_price: Current price from BuildersMART
        material_name: Name of the material
        price_type: Type of price being compared (median, min, max, avg)
        
    Returns:
        Base64 encoded PNG image string
    """
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Prepare data
    categories = ['Model Predicted', 'IndiaMART', 'BuildersMART']
    prices = [
        model_price if model_price is not None else 0,
        indiamart_price if indiamart_price is not None else 0,
        buildersmart_price if buildersmart_price is not None else 0
    ]
    colors = ['#2E86AB', '#F77F00', '#06A77D']
    
    # Create bars
    bars = ax.bar(categories, prices, color=colors, alpha=0.8, edgecolor='black', linewidth=1.5)
    
    # Add value labels on bars
    for bar, price in zip(bars, prices):
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'₹{height:,.0f}',
                   ha='center', va='bottom', fontsize=11, weight='bold')
        else:
            ax.text(bar.get_x() + bar.get_width()/2., 0,
                   'N/A',
                   ha='center', va='bottom', fontsize=10, style='italic', color='red')
    
    # Styling
    ax.set_ylabel('Price (₹)', fontsize=12, weight='bold')
    ax.set_title(f'Price Comparison: {material_name} ({price_type.title()})', 
                fontsize=14, weight='bold', pad=20)
    
    # Add note about model price being estimated from index
    ax.text(0.02, 0.02, 'Note: Model price is estimated from price index', 
           transform=ax.transAxes, fontsize=8, style='italic', color='gray',
           verticalalignment='bottom')
    
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    
    # Format y-axis with Indian numbering
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{x:,.0f}'))
    
    plt.tight_layout()
    
    # Convert to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    return f"data:image/png;base64,{img_base64}"


def create_comprehensive_visualization(historical_data: pd.DataFrame,
                                      prediction: Dict,
                                      scraper_results: Dict,
                                      material_name: str) -> Dict[str, str]:
    """Create both line graph and bar graph visualizations.
    
    Args:
        historical_data: DataFrame with historical price data
        prediction: Dict with model prediction results
        scraper_results: Dict with scraped prices from IndiaMART and BuildersMART
        material_name: Name of the material
        
    Returns:
        Dict with 'line_graph' and 'bar_graph' keys containing base64 image strings
    """
    # Extract prices from scraper results
    indiamart_price = None
    buildersmart_price = None
    
    if 'indiamart' in scraper_results and scraper_results['indiamart'].get('status') == 'available':
        indiamart_price = scraper_results['indiamart'].get('median')
    
    if 'buildersmart' in scraper_results and scraper_results['buildersmart'].get('status') == 'available':
        buildersmart_price = scraper_results['buildersmart'].get('median')
    
    # Convert price index to estimated actual price
    model_price_index = historical_data['price_index'].iloc[-1] if not historical_data.empty else None
    model_price = convert_index_to_price(model_price_index, material_name) if model_price_index is not None else None
    
    # Convert predicted value from index to actual price if it's an index
    if 'predicted_value' in prediction:
        pred_val = prediction['predicted_value']
        # If predicted value looks like an index (typically 80-200), convert it
        if pred_val is not None and 50 < pred_val < 300:
            prediction['predicted_value'] = convert_index_to_price(pred_val, material_name)
    elif model_price is not None:
        # Add predicted value to prediction dict if not present
        trend = prediction.get('trend', 'STABLE')
        # Simple prediction: adjust current price based on trend
        if trend == 'UP' or trend == '1' or trend == 1:
            prediction['predicted_value'] = model_price * 1.05  # 5% increase
        elif trend == 'DOWN' or trend == '-1' or trend == -1:
            prediction['predicted_value'] = model_price * 0.95  # 5% decrease
        else:
            prediction['predicted_value'] = model_price
    
    return {
        'line_graph': create_prediction_line_graph(historical_data, prediction, material_name),
        'bar_graph': create_price_comparison_bar_graph(
            model_price, indiamart_price, buildersmart_price, material_name
        )
    }


def create_multi_material_comparison(materials_data: List[Dict]) -> str:
    """Create a comparison chart for multiple materials.
    
    Args:
        materials_data: List of dicts with 'name', 'model_price', 'indiamart_price', 'buildersmart_price'
        
    Returns:
        Base64 encoded PNG image string
    """
    fig, ax = plt.subplots(figsize=(14, 8))
    
    x = np.arange(len(materials_data))
    width = 0.25
    
    model_prices = [m.get('model_price', 0) for m in materials_data]
    india_prices = [m.get('indiamart_price', 0) for m in materials_data]
    builder_prices = [m.get('buildersmart_price', 0) for m in materials_data]
    
    bars1 = ax.bar(x - width, model_prices, width, label='Model Predicted', color='#2E86AB', alpha=0.8)
    bars2 = ax.bar(x, india_prices, width, label='IndiaMART', color='#F77F00', alpha=0.8)
    bars3 = ax.bar(x + width, builder_prices, width, label='BuildersMART', color='#06A77D', alpha=0.8)
    
    ax.set_xlabel('Materials', fontsize=12, weight='bold')
    ax.set_ylabel('Price (₹)', fontsize=12, weight='bold')
    ax.set_title('Multi-Material Price Comparison', fontsize=14, weight='bold', pad=20)
    ax.set_xticks(x)
    ax.set_xticklabels([m['name'][:20] + '...' if len(m['name']) > 20 else m['name'] 
                        for m in materials_data], rotation=45, ha='right')
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    
    return f"data:image/png;base64,{img_base64}"
