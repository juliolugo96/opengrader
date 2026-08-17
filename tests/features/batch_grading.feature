Feature: Deterministic batch grading
  Instructors need to grade selected submissions efficiently
  while preserving fair, inspectable scores.

  Scenario: Grade selected submissions in parallel with partial credit and retries
    Given an assignment that awards half credit for exit code 2
    And submissions named alice, bob, and carol
    When I grade alice and bob with 2 workers and 1 retry
    Then the command succeeds
    And the JSON submissions are ordered alice then bob
    And alice earns 2.5 out of 5 points after 2 attempts
    And bob earns 5 out of 5 points after 1 attempt
    And the CSV report contains alice and bob but not carol

  Scenario: Reject a submission pattern that matches nobody
    Given an assignment that awards half credit for exit code 2
    And submissions named alice, bob, and carol
    When I grade the unmatched pattern nobody*
    Then the command fails with an unmatched pattern error
