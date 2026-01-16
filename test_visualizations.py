"""
Test script for visualization functions
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

from agentapp.visualizations import (
    create_prediction_line_graph,
    create_price_comparison_bar_graph,
    create_comprehensive_visualization,
    create_multi_material_comparison
)


def test_line_graph():
    """Test line graph generation"""
    print("Testing line graph generation...")
    
    # Create sample historical data
    dates = pd.date_range(end=datetime.now(), periods=12, freq='M')
    prices = [100, 102, 105, 103, 108, 110, 107, 112, 115, 113, 118, 120]
    
    historical_data = pd.DataFrame({
        'date': dates,
        'price_index': prices
    })
    
    prediction = {
        'trend': 'UP',
        'probability': 0.75,
        'predicted_value': 125
    }
    
    result = create_prediction_line_graph(historical_data, prediction, "Test Cement")
    
    if result.startswith('data:image/png;base64,'):
        print("✓ Line graph generated successfully")
        print(f"  Base64 length: {len(result)} characters")
    else:
        print("✗ Line graph generation failed")
    
    return result


def test_bar_graph():
    """Test bar graph generation"""
    print("\nTesting bar graph generation...")
    
    result = create_price_comparison_bar_graph(
        model_price=5200,
        indiamart_price=5450,
        buildersmart_price=5300,
        material_name="OPC 53 Grade Cement",
        price_type="median"
    )
    
    if result.startswith('data:image/png;base64,'):
        print("✓ Bar graph generated successfully")
        print(f"  Base64 length: {len(result)} characters")
    else:
        print("✗ Bar graph generation failed")
    
    return result


def test_comprehensive_visualization():
    """Test comprehensive visualization"""
    print("\nTesting comprehensive visualization...")
    
    # Historical data
    dates = pd.date_range(end=datetime.now(), periods=12, freq='M')
    prices = np.random.randint(100, 120, 12)
    historical_data = pd.DataFrame({
        'date': dates,
        'price_index': prices
    })
    
    # Prediction
    prediction = {
        'trend': 'STABLE',
        'probability': 0.65
    }
    
    # Scraper results
    scraper_results = {
        'buildersmart': {
            'status': 'available',
            'median': 5300,
            'min': 5000,
            'max': 5600
        },
        'indiamart': {
            'status': 'available',
            'median': 5450,
            'min': 5200,
            'max': 5800
        }
    }
    
    result = create_comprehensive_visualization(
        historical_data, prediction, scraper_results, "PPC Cement"
    )
    
    if 'line_graph' in result and 'bar_graph' in result:
        print("✓ Comprehensive visualization generated successfully")
        print(f"  Line graph: {len(result['line_graph'])} characters")
        print(f"  Bar graph: {len(result['bar_graph'])} characters")
    else:
        print("✗ Comprehensive visualization generation failed")
    
    return result


def test_multi_material_comparison():
    """Test multi-material comparison chart"""
    print("\nTesting multi-material comparison...")
    
    materials_data = [
        {
            'name': 'OPC 53 Grade Cement',
            'model_price': 5200,
            'indiamart_price': 5450,
            'buildersmart_price': 5300
        },
        {
            'name': 'TMT Steel Bars',
            'model_price': 62000,
            'indiamart_price': 63500,
            'buildersmart_price': 62800
        },
        {
            'name': 'River Sand',
            'model_price': 1800,
            'indiamart_price': 2100,
            'buildersmart_price': 1950
        }
    ]
    
    result = create_multi_material_comparison(materials_data)
    
    if result.startswith('data:image/png;base64,'):
        print("✓ Multi-material comparison generated successfully")
        print(f"  Base64 length: {len(result)} characters")
    else:
        print("✗ Multi-material comparison generation failed")
    
    return result


def save_test_image(base64_str, filename):
    """Save base64 image to file for visual inspection"""
    import base64
    
    if base64_str.startswith('data:image/png;base64,'):
        base64_str = base64_str.replace('data:image/png;base64,', '')
    
    img_data = base64.b64decode(base64_str)
    
    with open(filename, 'wb') as f:
        f.write(img_data)
    
    print(f"  Saved test image to: {filename}")


if __name__ == '__main__':
    print("=" * 60)
    print("Material Wise - Visualization Test Suite")
    print("=" * 60)
    
    try:
        # Run tests
        line_result = test_line_graph()
        bar_result = test_bar_graph()
        comprehensive_result = test_comprehensive_visualization()
        multi_result = test_multi_material_comparison()
        
        # Save sample images
        print("\n" + "=" * 60)
        print("Saving sample images...")
        print("=" * 60)
        
        os.makedirs('test_outputs', exist_ok=True)
        save_test_image(line_result, 'test_outputs/line_graph.png')
        save_test_image(bar_result, 'test_outputs/bar_graph.png')
        save_test_image(comprehensive_result['line_graph'], 'test_outputs/comprehensive_line.png')
        save_test_image(comprehensive_result['bar_graph'], 'test_outputs/comprehensive_bar.png')
        save_test_image(multi_result, 'test_outputs/multi_material.png')
        
        print("\n" + "=" * 60)
        print("All tests completed successfully! ✓")
        print("Check the 'test_outputs' folder for generated images.")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
