# Discovery Call Script

## Goal

Decide whether a 2-week QA Memory Pilot has a narrow, safe, measurable target.

## Opening

"We are not trying to replace your QA process. We are testing whether BQA-OS can
convert existing QA evidence into reusable workflows, specs, and validation
reports that reduce repeated context gathering."

## Qualification Questions

1. What QA workflow repeats every release?
2. Where does the current context live: tickets, chat, docs, logs, test code, or
   someone's memory?
3. What is the smallest module, service, or pipeline that is safe for a pilot?
4. Which inputs can be sanitized or made synthetic?
5. What test command or validation command proves useful output?
6. What output would the team actually reuse after two weeks?
7. Who signs off on safety and data boundaries?
8. Who is the QA owner for day-to-day feedback?

## Disqualifiers

Do not start the pilot if:
- the team cannot provide sanitized or synthetic inputs;
- success criteria are vague;
- the target scope is larger than one release area;
- the workflow requires credentials or production data in committed artifacts;
- no QA owner can review the output.

## Pilot Acceptance Draft

"The pilot succeeds if BQA-OS produces a local QA memory pack for `<target>` and
the QA owner confirms that at least one generated workflow or test spec is
reusable for the next release."

## Close

Confirm:
- target area;
- owner;
- input list;
- safety reviewer;
- first review date;
- expected validation command.
