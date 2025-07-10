Feature: Automated Admin User Setup
  As a new developer
  I want the admin user to be automatically configured during setup
  So that I can start developing immediately without manual Keycloak configuration

  Background:
    Given Keycloak is running
    And the AMS realm is configured

  Scenario: Automated admin user configuration during full setup
    Given I run the full automated setup
    When the Keycloak realm is imported
    Then the admin user should be automatically configured
    And the admin user should have proper credentials set
    And the admin user should have no required actions
    And the admin user should have admin role assigned
    And the UI client should have protocol mappers configured

  Scenario: Admin user can login immediately after setup
    Given the automated setup has completed successfully
    When I navigate to the AMS Portal login page
    And I enter admin credentials "admin" and "admin123"
    Then I should be successfully authenticated
    And I should see the admin home template
    And the JWT token should contain preferred_username
    And the JWT token should contain realm roles

  Scenario: Protocol mappers are configured correctly
    Given the automated setup has completed
    When I login as admin user
    Then the JWT token should contain "preferred_username" claim
    And the JWT token should contain "realm_access.roles" claim
    And the "realm_access.roles" should include "admin"
    And the "preferred_username" should be "admin"

  Scenario: Setup script handles existing admin user gracefully
    Given an admin user already exists in Keycloak
    And the admin user has required actions set
    When I run the automated setup
    Then the existing admin user should be updated
    And the required actions should be removed
    And the password should be set to "admin123"
    And the protocol mappers should be added or updated

  Scenario: Fresh client secret generation with admin user setup
    Given I run the automated setup multiple times
    When the Keycloak realm is recreated each time
    Then a fresh client secret should be generated each time
    And the admin user should be configured consistently
    And the config.yaml should be updated with the new secret
    And the admin user authentication should work with each setup