# Action Library Internal Pilot

Purpose: provide a small reviewed internal action-library source for runtime and
evidence-chain smoke tests. This document is not enough for commercial launch by
itself. It is only an internal pilot source that lets the system verify that
action-library evidence is wired through the same source registry, chunk schema,
runtime index, and evidence drawer chain as external sources.

## Scope

This source may support core prescription fields only for the workout patterns
listed below, and only when the generated card also passes the normal risk gate,
profile capacity gate, and protocol gate.

It must not be used for:

- medical diagnosis or treatment
- pain or chest-symptom decisions
- nutrition or fueling advice
- high-intensity replacement workouts after medical red flags
- race-day guarantees

## Shared Guardrails

- Every hard workout must include warmup and cooldown.
- Do not increase intensity when the runner reports acute pain, chest pain,
  dizziness, heat illness signs, or unusual shortness of breath.
- If fatigue is high or sleep is poor, downgrade intensity before adding volume.
- Keep easy and recovery runs conversational.
- Strength and mobility work are support sessions, not substitutes for medical
  rehabilitation when symptoms are present.

## Easy Run

Workout type: easy_run

Main set options:

- 30 to 45 min easy run in Z1-Z2
- 40 min conversational aerobic run
- 25 to 35 min recovery jog after a hard day

Intensity: Z1-Z2, conversational effort.

Objective: build aerobic volume without adding meaningful fatigue.

Warmup: 5 to 10 min very easy jog plus basic mobility.

Cooldown: 5 min walk or very easy jog.

Alternative: rest day or 30 min low-impact cross-training when fatigue is high.

## Long Run

Workout type: long_run

Main set options:

- 70 to 100 min easy long run in Z2
- 80 min easy run with the final 10 min steady but controlled
- 90 min aerobic run on rolling terrain without surges

Intensity: mostly Z2, no faster than steady aerobic effort unless specified.

Objective: improve aerobic durability and musculoskeletal tolerance.

Warmup: first 10 min very easy.

Cooldown: 5 to 10 min easy jog or walk.

Alternative: split into two shorter easy runs only when the plan explicitly
allows it and the runner is not injured.

## Threshold / Tempo

Workout type: tempo_run

Main set options:

- 3 x 8 min controlled threshold, 2 min easy jog recovery
- 2 x 12 min comfortably hard tempo, 3 min easy jog recovery
- 20 min continuous tempo when recent workload is stable

Intensity: upper Z3 to Z4, controlled and repeatable.

Objective: improve lactate-threshold tolerance without racing the workout.

Warmup: 15 min easy jog plus 4 short strides.

Cooldown: 10 min easy jog.

Alternative: 40 min easy run when fatigue, soreness, or sleep risk is present.

## Interval

Workout type: interval_run

Main set options:

- 5 x 3 min hard but controlled, 2 min easy jog recovery
- 6 x 800 m at 5K to 10K effort, 2 to 3 min jog recovery
- 10 x 1 min fast, 1 min easy when returning from a down week

Intensity: Z5 only when the runner is healthy and prepared.

Objective: develop speed reserve and aerobic power.

Warmup: 15 to 20 min easy jog, drills, and 4 to 6 strides.

Cooldown: 10 to 15 min easy jog.

Alternative: fartlek or easy aerobic run when risk gate downgrades intensity.

## Hill Repeats

Workout type: hill_repeats

Main set options:

- 8 x 20 sec hill strides, walk-down recovery
- 6 x 45 sec controlled uphill, easy jog down
- 10 x 10 sec steep hill sprint only for resilient runners

Intensity: strong form-focused effort, not all-out fatigue.

Objective: improve running mechanics, stiffness, and strength endurance.

Warmup: 15 min easy jog plus dynamic mobility.

Cooldown: 10 min easy jog.

Alternative: flat strides when downhill running or hill mechanics increase pain.

## Recovery / Mobility Support

Workout type: recovery_support

Main set options:

- 20 to 30 min recovery jog plus 10 min mobility
- 30 min bike or elliptical at easy effort
- rest day plus calf, hip, and thoracic mobility

Intensity: Z1 or lower aerobic support.

Objective: preserve routine and circulation while reducing training stress.

Warmup: start very easy.

Cooldown: breathing reset and gentle mobility.

Alternative: full rest when pain, illness, or medical red flags are present.

## Review Boundary

Review status: approved internal pilot.

Prescription permission: can_write_core for the listed action-library patterns
only. This permission is not a commercial launch approval. Commercial readiness
still requires enough approved sources, live RAG-vs-base evaluation, domain-pack
coverage, and production evidence-chain audits.
