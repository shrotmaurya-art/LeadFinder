## Known agent / "vibe coding" failure patterns -- explicitly forbidden
These are mistakes AI coding agents make often enough to name directly.
Catching yourself about to do one of these is a stop signal, not a nudge.
1. Do not write against a file you have not actually opened and read this
   session. Never assume a function's signature or a file's contents from
   memory, training data, or this guide's prose -- view the real file
   first, every time, even if you "remember" writing it earlier.
2. Do not report a task as done without actually running its Verification
   steps and looking at the real output. "This should work" or "this
   satisfies the requirement" is not evidence -- a passing test run is.
3. Do not invent a library, method, or API you are not certain exists.
   A plausible-sounding function name is not a real function. If unsure,
   check requirements.txt or the library's actual installed version
   instead of guessing.
4. Do not silently expand scope. Touch only the files named in the task's
   Prompt. If another file genuinely needs to change too, stop and say so
   instead of editing it unasked.
5. Do not present partial work as finished. If a task cannot be fully
   completed this turn, say exactly what remains undone -- do not round up
   "mostly working" to "done."
6. Do not duplicate logic that already exists elsewhere in the codebase
   (e.g. re-implementing normalize_phone inline instead of importing it).
   Search the codebase for an existing function before writing a new one.
7. Do not catch an exception just to make an error disappear. A caught
   exception is logged and either handled meaningfully or re-raised --
   never a bare pass that hides a real failure.
8. Do not hardcode a value "temporarily" with a plan to fix it later.
   It will not get fixed later -- do it right the first time or flag it.
9. Do not add a dependency, config flag, or abstraction layer that was not
   asked for "in case it's needed." Build exactly what the task specifies,
   nothing speculative.
10. Do not mark a Verification checklist item true from reasoning about
    what the code should do. Execute it and read the actual result.