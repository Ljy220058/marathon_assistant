# Audit And Repair Contract

## Audit Layers

| Audit | Question |
|---|---|
| Safety Audit | Does the candidate violate red-flag, injury, fatigue, recovery, or environment rules? |
| Evidence Audit | Is every prescription claim grounded in eligible evidence or approved actions? |
| Protocol Audit | Does the plan satisfy HMP phase, weekly volume, intensity, progression, and recovery rules? |
| Trace Audit | Are risk level, evidence IDs, action IDs, rules, and repair log present? |

## Bounded Repair

Allowed repairs:

- delete unsupported explanatory claims
- lower intensity
- reduce volume
- add rest or recovery day
- replace with approved action
- convert full plan to partial answer
- refuse when required by R3 or unrepairable conflict

Forbidden repairs:

- create new evidence IDs
- bypass red flags
- turn medical risk into training advice
- invent actions outside the approved action library
- hide a rule violation by changing only wording

## Repair Output

```json
{
  "audit_result": "repair_required",
  "repair_actions": [
    {
      "rule_id": "risk.R2.fatigue",
      "before": "tempo intervals",
      "after": "easy run or rest",
      "reason": "fatigue risk outranks performance optimization"
    }
  ],
  "final_status": "partial_answer"
}
```
