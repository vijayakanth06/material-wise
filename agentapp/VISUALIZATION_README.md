# Material Wise - Visualization Module

This module provides visualization capabilities for the Material Wise prediction system.

## Features

### 1. Line Graph - Price Trend Prediction
Shows historical price index over time with predicted future trend:
- Historical data points (last 12 months)
- Trend arrow (UP ↑, DOWN ↓, or STABLE →)
- Confidence percentage
- Color-coded predictions

### 2. Bar Graph - Price Comparison
Compares prices from three sources:
- Model predicted price (from historical price index)
- Current IndiaMART price (scraped)
- Current BuildersMART price (scraped)

### 3. Multi-Material Comparison
Side-by-side comparison of multiple materials across all three price sources.

## Usage

### In API (Automatic)
The `/api/predict` endpoint automatically generates both visualizations:

```python
# Visualization data is returned in the response
{
    "visualizations": {
        "line_graph": "data:image/png;base64,...",
        "bar_graph": "data:image/png;base64,..."
    }
}
```

### Standalone Usage

```python
from agentapp.visualizations import create_comprehensive_visualization
import pandas as pd

# Prepare historical data
historical_data = pd.DataFrame({
    'date': pd.date_range(end='2026-01-15', periods=12, freq='M'),
    'price_index': [100, 102, 105, 103, 108, 110, 107, 112, 115, 113, 118, 120]
})

# Prediction data
prediction = {
    'trend': 'UP',
    'probability': 0.75,
    'predicted_value': 125
}

# Scraper results
scraper_results = {
    'buildersmart': {'status': 'available', 'median': 5300},
    'indiamart': {'status': 'available', 'median': 5450}
}

# Generate visualizations
charts = create_comprehensive_visualization(
    historical_data, 
    prediction, 
    scraper_results, 
    "OPC 53 Grade Cement"
)

# charts['line_graph'] and charts['bar_graph'] contain base64-encoded PNG images
```

## Testing

Run the test suite:

```bash
python test_visualizations.py
```

This will:
- Generate sample visualizations
- Save PNG files to `test_outputs/` folder
- Verify all functions work correctly

## Output Format

All visualization functions return base64-encoded PNG images as strings:
- Format: `data:image/png;base64,<encoded_data>`
- Can be directly embedded in HTML `<img>` tags
- No file I/O required

## Dependencies

- matplotlib >= 3.8
- pandas >= 2.0
- numpy >= 1.24

## Chart Styling

- Colors:
  - Model/Historical: `#2E86AB` (Blue)
  - IndiaMART: `#F77F00` (Orange)
  - BuildersMART: `#06A77D` (Green)
  - UP trend: `#06A77D` (Green)
  - DOWN trend: `#D62828` (Red)
  - STABLE trend: `#F77F00` (Orange)

- Font: System default (matplotlib)
- DPI: 100 (web-optimized)
- Format: PNG with transparent background support

## Notes

- Uses non-GUI backend (`Agg`) for server environments
- All chart generation is stateless (no side effects)
- Memory-efficient: charts generated on-demand, not cached
- Thread-safe: no shared state between function calls
