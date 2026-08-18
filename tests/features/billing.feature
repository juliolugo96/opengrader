Feature: Hosted subscription billing
  Hosted operators need paid access and reliable usage metering without charging local grading.

  Scenario: Activate a hosted tenant and meter accepted grading work
    Given a hosted OpenGrader billing API
    When I try to create grading work without a subscription
    Then hosted grading requires payment
    When Stripe sends a signed active subscription event
    Then the hosted tenant becomes entitled
    When I create an entitled grading job
    Then one durable usage unit is reported to Stripe
    And replaying the Stripe event does not apply it twice
