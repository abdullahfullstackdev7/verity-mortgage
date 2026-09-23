# Internal Underwriting Guidelines (Reference Corpus)

This is a short internal reference corpus used to ground the automated
underwriter-summary narrative. It describes how this platform classifies
and responds to the discrepancy types its rules engine can raise. It is
written for this system specifically and does not represent any real
institution's policy.

## Income Verification Tolerance

Applicant income stated on the application is cross-checked against the
pay stub's annualized gross pay and the W-2's Box 1 wages. A variance of
up to 10 percent from the stated figure is considered normal rounding and
pay-cycle noise and is not flagged. A variance between 10 and 20 percent
is a minor discrepancy and should be noted in the summary as worth a
follow-up question to the applicant. A variance beyond 20 percent is a
major discrepancy and should be treated as a material misstatement of
income that materially affects affordability; the summary should
recommend the case not be auto-approved.

## Employer Identity Verification

The employer name on the application is compared against the employer
name printed on the pay stub and W-2 using semantic similarity rather
than exact text matching, since OCR and formatting differences are
expected (for example "Acme Corp" versus "Acme Corporation"). A close
match is not flagged. A moderate mismatch is minor and usually reflects a
DBA name, an OCR error, or a recent employer name change, and should be
mentioned as a low-priority note. A large mismatch is major and should be
treated as a potential identity or employment inconsistency worth direct
underwriter attention before any approval.

## Bank Deposit Consistency

Recurring payroll-labeled deposits on the bank statement are summed and
compared against the net income that would be expected from the stated
gross income for that statement period. A deposit total within 15 percent
of the expected figure is normal (net pay varies with benefits
elections, overtime, and pay-date timing). A variance between 15 and 30
percent is minor and worth noting. A variance beyond 30 percent is major
and suggests the applicant's actual take-home pay may not support the
stated income, and should be flagged clearly in the recommendation.

## Debt-to-Income Ratio Review

The debt-to-income ratio is recomputed by holding the applicant's implied
monthly debt obligation fixed and substituting verified income in place
of stated income. A shift of up to 3 percentage points from the stated
DTI is normal. A shift between 3 and 6 percentage points is minor and
should be mentioned, since it indicates the true affordability picture is
somewhat worse than stated. A shift beyond 6 percentage points is major
and should be treated as a significant affordability concern.

## Severity Classification and Escalation

Every discrepancy is labeled minor or major. A case with no discrepancies,
or only minor discrepancies across all checks, is a strong candidate for
straightforward processing, though a human underwriter should still make
the final call on anything other than a fully clean case. A case with any
major discrepancy should never be described as low-risk in the summary,
regardless of how clean the other checks are, since a single material
misstatement is enough to warrant closer review.

## Summary and Recommendation Guidance

The narrative should be concise, factual, and specific: name which fields
were checked, which (if any) were flagged, and at what severity, rather
than giving a generic risk statement. The recommendation label should be
"approve" only when there are no discrepancies at all. It should be
"refer" when there are only minor discrepancies, since those warrant a
human look but are not disqualifying on their own. It should be "deny"
only when there is at least one major discrepancy that directly
contradicts the applicant's stated financial position, and even then the
narrative should say plainly that a human underwriter makes the final
decision, not the automated summary.
