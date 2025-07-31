# t1-copilot
Live countdown &amp; alert layer for SEC T+1: tracks every broker’s alloc/affirm deadlines, flashes red when you’re about to miss them.

T+1 Copilot is an MIT-licensed toolkit that
	•	ingests trade tickets,
	•	looks up the correct broker/custodian SLA from broker_sla.yaml,
	•	skips US-market holidays automatically, and
	•	turns rows yellow @ <60 min and red @ <30 min so you never blow the new same-day-affirmation rule (SEC 15c6-2).
