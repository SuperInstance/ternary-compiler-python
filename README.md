# ternary-compiler-python

Ternary expression compiler in Python. Parses mathematical expressions, builds an AST, optimizes with constant folding, and emits ternary bytecode for the Z₃ VM.

## Why This Matters

This is the Python reference implementation of the ternary compiler — useful for prototyping ternary programs before porting to Rust for GPU execution. Shows the complete pipeline from source to bytecode.

## What's Inside

- **Lexer/Parser**: Mathematical expressions with Z₃ operators
- **AST**: Expression tree with ternary-aware nodes
- **Optimizer**: Constant folding, dead code elimination
- **Bytecode emitter**: Produces opcodes for the ternary VM
- **REPL**: Interactive ternary expression evaluation

## The Five-Layer Stack

```
┌─────────────────┐
│  cudaclaw        │  Persistent GPU kernels, warp consensus, SmartCRDT
├─────────────────┤
│  cuda-oxide      │  Flux → MIR → Pliron → NVVM → PTX compiler
├─────────────────┤
│  flux-core       │  Bytecode VM + A2A agent protocol
├─────────────────┤
│  pincher         │  "Vector DB as runtime, LLM as compiler"
├─────────────────┤
│  open-parallel   │  Async runtime (tokio fork)
└─────────────────┘
```

## Installation

```bash
pip install ternary-compiler
```

## Usage

```python
from ternary_compiler import compile_expr, VM

# Compile and run
bytecode = compile_expr("(1 * -1) + 1")  # = 0
result = VM().execute(bytecode)
print(result)  # 0
```

## License

Apache-2.0
