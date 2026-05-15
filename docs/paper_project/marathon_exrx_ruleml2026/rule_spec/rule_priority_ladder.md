# Rule Priority Ladder

The rule layer is the reasoner of record.

```text
medical red flags
> injury / fatigue / environment risk
> evidence insufficiency
> protocol hard constraints
> capacity budget
> temporal progression
> user constraints
> performance optimization
> natural-language preference
```

## Conflict Examples

| Conflict | Winner | Reason |
|---|---|---|
| user wants intervals with chest pain | medical red flags | R3 refusal |
| user wants long run despite worsening knee pain | injury risk | downgrade or stop |
| user asks for exact fueling but no evidence | evidence insufficiency | explanation only or ask clarification |
| user wants 30 percent mileage jump | capacity budget | cap progression |
| user wants peak workout during taper | temporal progression | preserve taper |
| user prefers hard workout over recovery | performance optimization loses | recovery is required |

## Auditor Decision Labels

| Label | Meaning |
|---|---|
| pass | candidate satisfies contract |
| repair_required | bounded repair can make it compliant |
| partial_answer | safe explanation possible, full prescription blocked |
| ask_clarification | missing profile or risk information blocks prescription |
| refused | R3 or unrepairable unsafe request |
