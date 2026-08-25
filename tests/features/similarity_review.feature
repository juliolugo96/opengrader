Feature: Assignment similarity review
  Instructors need explainable similarity evidence without an automated misconduct verdict.

  Scenario: Review structurally similar written submissions
    Given a configured similarity review API
    And a written assignment with two similar PDF submissions
    When I start an assignment similarity review
    Then the review completes with explainable evidence
    And the review remains available as an immutable report
    And the similarity workflow appears in the audit trail
