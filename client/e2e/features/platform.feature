Feature: OpenGrader full-platform persistence
  Instructors need confidence that browser actions reach the real API and durable storage.

  Scenario: Create and reload an assignment through the complete platform
    Given credentials for the isolated platform API
    When I create a persisted written assignment through the platform
    Then the assignment remains visible after a browser reload
    And the real audit trail records the assignment creation
