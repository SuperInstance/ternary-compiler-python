# ternary-compiler-python

Python implementation of the ternary strategy compiler — compile strategies into optimized lookup tables.

## Install

```bash
pip install .
```

## Usage

```python
from ternary_compiler import StrategyIR, compile, CompiledPolicy

# Define a simple ternary strategy
strategy = StrategyIR(
    conditions=[
        {"field": "x", "op": ">", "value": 0},
        {"field": "x", "op": "<", "value": 10},
        {"field": "y", "op": "==", "value": 5},
    ],
    actions=[
        {"type": "accept", "priority": 1},
        {"type": "reject", "priority": 0},
        {"type": "accept", "priority": 2},
    ],
)

policy = compile(strategy)
result = policy.evaluate({"x": 5, "y": 5})
print(result)  # "accept"
```

## Development

```bash
PYTHONPATH=src pytest tests/ -v
```

## License

MIT
