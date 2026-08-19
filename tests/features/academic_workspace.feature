Feature: Professor assignment workspace
  Professors need to organize automated and written work without editing engine configuration files.

  Scenario: Organize and launch an automated course assignment
    Given a configured professor assignment API
    When I create an automated assignment for a course section
    Then the assignment is stored with its institution, period, and section
    When I launch that saved assignment against a submissions folder
    Then OpenGrader creates a durable job from a generated definition

  Scenario: Associate a PDF submission with written course work
    Given a configured professor assignment API
    When I create a written assignment and upload a PDF submission
    Then the PDF submission is listed under that assignment
