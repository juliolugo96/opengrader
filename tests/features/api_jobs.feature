Feature: Durable authenticated grading API
  Instructors need to submit grading work without blocking an HTTP request
  and retrieve the result after it is processed.

  Scenario: Reject an unauthenticated job submission
    Given a configured OpenGrader API
    When I submit a job without an API key
    Then the API responds with unauthorized

  Scenario: Submit, process, and retrieve a durable grading job
    Given a configured OpenGrader API
    And a passing local grading fixture
    When I submit an authenticated local grading job
    Then the API accepts a queued job
    And the job eventually succeeds
    And I can retrieve its grading result
    And its lifecycle appears in the audit trail
    And the succeeded job survives an API restart
