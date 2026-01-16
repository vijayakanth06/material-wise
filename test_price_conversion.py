"""Test price index to actual price conversion"""
import sys
sys.path.append('c:/Users/vikym/Documents/GitHub/material-wise')

from agentapp.visualizations import convert_index_to_price, estimate_base_price

# Test cases
test_materials = [
    ("OPC-53 Grade Cement", 136.7),
    ("Ordinary Portland cement", 136.7),
    ("PPC", 126.1),
    ("TMT Steel", 143.5),
    ("White Cement", 138.1),
]

print("Price Index to Actual Price Conversion Test")
print("=" * 70)
print()

for material, price_index in test_materials:
    base_price = estimate_base_price(material)
    actual_price = convert_index_to_price(price_index, material)
    
    print(f"Material: {material}")
    print(f"  Price Index: {price_index}")
    print(f"  Base Price (2012): ₹{base_price:.2f}")
    print(f"  Estimated Current Price: ₹{actual_price:.2f}")
    print(f"  Growth: {((price_index/100) - 1)*100:.1f}%")
    print()

print("\nExpected vs Estimated Comparison:")
print("-" * 70)
print(f"OPC Cement - Market: ₹400-420, Estimated: ₹{convert_index_to_price(136.7, 'cement'):.2f}")
print(f"Difference: {((convert_index_to_price(136.7, 'cement') / 410) - 1) * 100:.1f}%")
