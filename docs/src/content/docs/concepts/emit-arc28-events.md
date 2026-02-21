---
title: Emitting ARC-28 Events
description: Code examples for emitting ARC-28 events from Algorand smart contracts.
---

# Emitting ARC-28 Events

To emit ARC-28 events from your smart contract you can use the following syntax.

## Algorand Python

```python
@arc4.abimethod
def emit_swapped(self, a: arc4.UInt64, b: arc4.UInt64) -> None:
    arc4.emit("MyEvent", a, b)
```

OR using a struct:

```python
class MyEvent(arc4.Struct):
    a: arc4.String
    b: arc4.UInt64

# ...

@arc4.abimethod
def emit_swapped(self, a: arc4.String, b: arc4.UInt64) -> None:
    arc4.emit(MyEvent(a, b))
```

## Algorand TypeScript

Using a named type (the type name is used as the event name):

```typescript
import { Contract, emit } from "@algorandfoundation/algorand-typescript";

type MyEvent = {
  stringField: string;
  intField: uint64;
};

class MyContract extends Contract {
  @abimethod()
  emitMyEvent(stringField: string, intField: uint64): void {
    emit<MyEvent>({ stringField, intField });
  }
}
```

OR using a struct:

```typescript
import { Contract, emit } from "@algorandfoundation/algorand-typescript";
import { Struct } from "@algorandfoundation/algorand-typescript/arc4";

class MyEvent extends Struct<{ stringField: string; intField: uint64 }> {}

class MyContract extends Contract {
  @abimethod()
  emitMyEvent(stringField: string, intField: uint64): void {
    emit(new MyEvent({ stringField, intField }));
  }
}
```

OR using an explicit event name with positional arguments:

```typescript
import { emit } from "@algorandfoundation/algorand-typescript";

// ...

emit("MyEvent(string,uint64)", stringField, intField);
```