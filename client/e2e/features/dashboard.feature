Feature: OpenGrader operations dashboard
  Instructors need a complete and inspectable view of durable grading work.

  Background:
    Given saved OpenGrader API credentials
    And a deterministic grader API

  Scenario: Review and paginate the complete jobs history
    When I open the jobs dashboard
    Then the dashboard reports 11 total jobs
    And the first jobs page contains 10 rows
    When I move to the next jobs page
    Then the remaining job is visible

  Scenario: Inspect a completed gradebook and export reports
    When I open the completed job
    Then I see the returned cohort totals
    When I expand the student and test results
    Then I see semantic exit-code and timeout badges
    And I can download both result formats

  Scenario: Trace the authenticated audit history
    When I open the audit trail
    Then I see the chronological job lifecycle and key fingerprint
