"""Fictional demonstration; does not load private restaurant data."""
import json
from pathlib import Path
from src.server_report import calculate, write_report

config = json.loads(Path('config.example.json').read_text())
reports = {
    'sales': {
        'Server A': {'net_sales': 1000, 'covers': 50, 'discount': 20},
        'Server B': {'net_sales': 3000, 'covers': 100, 'discount': 30},
    },
    'beverage': {
        'Server A': {'beverage_sales': 190, 'net_sales': 1000},
        'Server B': {'beverage_sales': 600, 'net_sales': 3000},
    },
    'turns': {
        'Server A': {'avg_minutes': 40, 'checks': 25},
        'Server B': {'avg_minutes': 45, 'checks': 50},
    },
}
result = calculate(config, reports)
result['data_type'] = 'FICTIONAL DEMONSTRATION — not restaurant results'
print(write_report(result, 'demo', 'outputs'))
