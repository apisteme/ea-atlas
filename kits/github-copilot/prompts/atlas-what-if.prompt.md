---
name: atlas-what-if
description: Model a what-if scenario or a change on the atlas with the impact engine
argument-hint: the event or change, for example "the policy admin system is down for a day"
agent: agent
---
Use the enterprise-architecture-atlas skill in Analyse mode on `ea-atlas/`: ${input:question:what happens if ...}

Run the impact engine rather than reasoning from memory. Do not change the model. Report the impact level, what goes down or degrades and why, journeys and roles affected, critical functions, the slowest recovery time, the cost effect and the checks raised, and say which inputs are illustrative.
