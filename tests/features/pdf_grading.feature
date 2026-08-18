Feature: Manual PDF grading
  Instructors need to grade document submissions with structured and page-specific feedback.

  Scenario: Upload, grade, annotate, and export a PDF submission
    Given a configured PDF grading API
    And a valid two-page PDF submission
    When I upload the PDF for manual grading
    Then the PDF is accepted as a draft
    When I finalize a rubric grade with a page annotation
    Then the finalized PDF grade reports the rubric total
    And the feedback PDF preserves the page comment and structured feedback
    And the PDF workflow appears in the audit trail
