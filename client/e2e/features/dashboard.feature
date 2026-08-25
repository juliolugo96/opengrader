Feature: OpenGrader operations dashboard
  Instructors need a complete and inspectable view of durable grading work.

  Background:
    Given saved OpenGrader API credentials
    And a deterministic grader API

  Scenario: Create and organize written work for an academic section
    When I open the assignment workspace
    And I create a written assignment for a course section
    Then the assignment is grouped by institution, course, period, and section
    When I switch the interface to Spanish
    Then the professor navigation is shown in Spanish

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

  Scenario: Upload, annotate, and finalize a PDF grade
    When I open PDF grading
    And I upload a two-page PDF submission
    Then I see the PDF grading workspace
    When I score the rubric and add a page annotation
    And I finalize the PDF grade
    Then I see the finalized rubric total
    And I can download the annotated feedback PDF

  Scenario: Inspect assignment-scoped similarity evidence
    When I open similarity review for an assignment with two submissions
    And I start the structural review
    Then I see explainable overlap and the human-review warning

  Scenario: Inspect hosted subscription and meter delivery
    When I open billing and usage
    Then I see an active hosted subscription
    And I see accepted, reported, and pending usage units

  Scenario: Import a Canvas assignment and preview grade synchronization
    When I open LMS integrations
    Then I see the configured Canvas account
    When I import a Canvas assignment for a course section
    Then the assignment is linked for grade synchronization
    When I preview its grade synchronization
    Then I see a dry-run delivery report

  Scenario: Compare transparent product plans
    When I open product plans
    Then I see Community, Hosted, and Institution options
    And roadmap capabilities are labeled as planned
    And Canvas synchronization is labeled as available now
