Feature: Canvas learning-management integration
  Instructors should move assignments and grades without format lock-in.

  Scenario: Import a Canvas assignment and synchronize finalized grades
    Given a configured Canvas integration
    When I import a Canvas assignment into a course section
    Then the local assignment is linked to the Canvas assignment
    When I finalize a linked PDF grade
    And I synchronize the assignment grades using SIS identifiers
    Then Canvas receives the percentage grade once
    And repeating the synchronization skips the delivered grade
