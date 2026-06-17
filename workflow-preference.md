# AlpMark Workflow Preference

- Explain what will change, why it changes, and where before making edits.
- For every step, teach in simple English before action:
	- Use this exact structure explicitly:
		- What it is.
		- What it does.
		- Why now.
		- Simple terminology.
	- Explain it in AlpMark context before action.
	- Then perform the action.
	- Then explain the result and what changed.
- After each completed task, include a recap in simple English:
	- What was completed.
	- Why it matters for the product.
	- Terminology used in that task with plain-English definitions.
- At the start of each new milestone, first create/update the chat todo list (top task list) from tasks.md before beginning implementation.
- Work one task at a time from the MS task list shown in chat.
- Pause after each task so questions can be asked before moving on.
- Keep the user oriented on the product and code at all times.
- Do not batch through tasks without confirming the current step.
- After every task implementation, run all three quality checks in order before marking the task complete:
	1. `ruff check` — lint and style
	2. `mypy` — type safety
	3. `pytest` — tests
	- All three must pass with zero errors before the task is considered done.
	- Fix any failures before pausing for questions.
