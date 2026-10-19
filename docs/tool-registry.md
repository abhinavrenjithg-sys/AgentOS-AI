# Initial tool registry

| Tool | Effect | Limits |
| --- | --- | --- |
| `research_public_pages` | Read public HTTP(S) page content | URL policy, timeout, redirect and response-size limits |
| `generate_csv` | Write a local run-scoped CSV | Fixed columns from extracted records |
| `prepare_email_draft` | Create a local subject/body output | Never sends email |

The planner schema only permits these names. Every unsupported tool fails validation. Inputs and outputs are recorded as JSON on the step run. The HTTP reader is not browser automation; JavaScript-rendered pages may have incomplete results.
